"""Small task recipes and story settings carried by the existing conversation."""
import json


TASKS = {
    ('appreciation', '文学点评'): '按“整体印象、语言与意象、结构与节奏、可改进之处”组织点评。摘引简短原句支撑判断，不擅自重写原文。',
    ('appreciation', '情感点评'): '按“原文可见的情绪线索、可能的情绪变化、其他解释、仍未知的信息”点评。避免给人物贴标签，不把读心式推测当事实。',
    ('appreciation', '读者视角'): '以普通读者身份描述初读感受、最有共鸣的细节、可能产生的疑问。明确这是读者的理解，不代表作者的唯一意图。',
    ('appreciation', '逐段批注'): '按每篇素材提供的段落编号逐段回应。每条采用“《文章标题》第N段｜原句摘录｜批注”的形式；重点讲表达、情绪和读者理解。只在回复中批注，不修改日记。不合并或跳过段落；如篇幅不足，明确最后完成的段落。',
    ('analysis', '人物分析'): '仅依据已选文章中的人物记载，围绕用户指定的分析对象，整理行为、关系变化和反复出现的表达。每项注明文章标题和可见日期；分开事实、推测、未知。无法确认同名是否同人时保留歧义。',
    ('analysis', '事件整理'): '整理事件表：可确认时间、事件、参与者、来源文章、待确认信息。将有原文依据的因果与推测分开；不为未知日期补造具体年月日。',
    ('analysis', '跨时间分析'): '先按已知日期整理时间顺序，再比较情绪、人物关系或主题的变化。未知日期和时间线之外的材料单独说明，不强行插入确定时间线。不要由少量记录推导稳定人格或确定因果。',
    ('analysis', '文章关联'): '按共同人物、事件、地点、意象、主题寻找文章之间的联系。每条列出具体文章及依据，区分明确关联与可能关联；矛盾之处和缺失信息也要列出。',
    ('writing', '直接创作'): '依据所选体裁和故事设定完成一篇创作。尊重人物设定、大纲和连续性备忘；没有提供的部分允许合理虚构，作品标注虚构。',
    ('writing', '故事大纲'): '生成可修改的故事大纲：核心主题、主线冲突、人物弧线、起承转合、分章梗概及伏笔安排。只列规划，不直接展开整篇正文。',
    ('writing', '人物设定'): '为本故事拟定人物卡：姓名或称呼、身份、目标、性格、关系、秘密或矛盾、成长方向。区分来自记录的素材与虚构补充，不读取其他人物资料。',
    ('writing', '生成章节'): '只写当前指定的一章。参考已有大纲、人物卡、连续性备忘和本对话已完成的章节，避免重复上一章；正文以“第N章 标题”开头，并明确为虚构创作。',
    ('writing', '续写下一章'): '接续本对话已有情节，只写当前指定的一章。保持人物称呼、时间、地点、视角与未解决线索一致；没有已写章节时说明这是起始章，不假装读过不存在的前文。',
    ('writing', '连续性整理'): '仅整理当前对话中已有的故事内容，输出可复制的连续性备忘：人物现状、已发生事件、时间地点、未解伏笔、后续必须保持的设定。区分已写内容与尚未发生的规划，不添加新情节。',
    ('writing', '整合现有章节'): '整合本次所选材料与本对话已有章节，统一称呼、视角与衔接，保留章节标题。不要声称整合了未提供的章节；明确列出需要补充的缺口。',
}
STORY_FIELDS = ('title', 'outline', 'characters', 'continuity')
STORY_STEPS = ('直接创作', '故事大纲', '人物设定', '生成章节', '续写下一章', '连续性整理', '整合现有章节')
STORY_START = '【故事设定 JSON】\n'
STORY_END = '\n【故事设定结束】'


def instruction_field(instruction, label):
    prefix = label + '：'
    return next((line[len(prefix):] for line in instruction.splitlines() if line.startswith(prefix)), '')


def task_guide(mode, instruction):
    kind = instruction_field(instruction, '步骤' if mode == 'writing' else '类型')
    return TASKS.get((mode, kind), '')


def numbered_paragraphs(body):
    return [{'number': index, 'text': paragraph} for index, paragraph in
            enumerate((line.strip() for line in body.splitlines() if line.strip()), 1)]


def encode_story(notes, step, chapter):
    state = {key: notes.get(key, '') for key in STORY_FIELDS}
    state.update(step=step, chapter=int(chapter))
    return STORY_START + json.dumps(state, ensure_ascii=False, indent=2) + STORY_END


def decode_story(instruction):
    if STORY_START not in instruction:
        return None
    try:
        raw = instruction.split(STORY_START, 1)[1].split(STORY_END, 1)[0]
        state = json.loads(raw)
        if not isinstance(state, dict):
            return None
        result = {key: state.get(key, '') if isinstance(state.get(key, ''), str) else '' for key in STORY_FIELDS}
        result['step'] = state.get('step') if state.get('step') in STORY_STEPS else STORY_STEPS[0]
        result['chapter'] = max(1, min(999, int(state.get('chapter', 1))))
        return result
    except (ValueError, TypeError):
        return None

import html
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from northdiary.storage.database import Database
from northdiary.storage.people import PeopleRepository
from northdiary.storage.repository import ArticleRepository
from northdiary.services.attachments import AttachmentService
from PySide6.QtCore import QSettings

root = Path(sys.argv[1])
if root.exists() and any(root.iterdir()):
    raise SystemExit('展示目录非空，停止生成，避免覆盖已有内容。')
rng = random.Random(3179)
db = Database(root)
repo = ArticleRepository(db); people = PeopleRepository(db); attachments = AttachmentService(db)
profiles = [
 ('林知夏','@知夏','同学','摄影社第一次外拍，她把备用电池借给了我。'),
 ('陈屿','@小屿','朋友','在旧书店找同一本书，从书架两端同时伸出手。'),
 ('许星遥','@星遥','社团伙伴','天文社迎新夜，一起等到云层散开。'),
 ('周以宁','@以宁','室友','搬进宿舍那天，一起组装了摇摇晃晃的小书架。'),
 ('沈书禾','@书禾','同学','课程小组讨论，把一团乱的想法画成了流程图。'),
 ('陆南舟','@南舟','旅伴','山路休息站遇见，后来同行走完最后一段路。'),
 ('江晚晴','@晚晴','朋友','校园广播站的雨天歌单征集。'),
 ('顾言川','@言川','项目伙伴','一次创意活动中，负责把我们的纸上草图做出来。'),
 ('宋予安','@予安','家人','从小一起长大，每次回家都约着去河边散步。'),
 ('唐可颂','@可颂','社团伙伴','烘焙活动里，做出了形状最自由的一盘饼干。'),
 ('叶听澜','@听澜','老师','读书分享会上认识，她鼓励我把观察写下来。'),
 ('程望舒','@望舒','朋友','在城市漫步活动中一起找到了地图上没有标出的台阶。'),
]
persons=[]
for i,(name,code,relation,how) in enumerate(profiles):
    persons.append(people.create(name,code,birth_date=f'{1998+i%7}-未知-未知',
        met_date=f'{2023+i%3}-{1+i%10:02d}-未知',met_how=how+'（虚构展示资料）',
        relationships=[relation],temporary_relationships=['海边同行'] if i==5 else [],
        pinned=int(i in (0,1)),starred=int(i in (0,2,4))))
stories = [
 ('春天从一杯热茶开始','生活片段','窗边的光比昨天多停留了一会儿。杯沿有一圈薄雾，楼下的人推着自行车经过，车铃声很轻。','没有急着安排一整天，只在纸上写下三件想做的小事。原来慢下来，也可以是一种认真。',['日常','春日']),
 ('雨后的图书馆','校园日记','雨停后，我们绕着积水走进图书馆。书页有干燥的气味，玻璃上还挂着几颗没有滑落的水珠。','把难题留在草稿纸上，把此刻留在日记里。今天的收获不是多读了多少页，而是终于愿意安静地坐下来。',['校园','阅读']),
 ('去海边等一次日落','旅行手记','傍晚的海风把说话声吹得很远。我们脱下鞋子，踩过还温热的沙，追着潮水留下的细线往前走。','太阳落下去之后，天空反而更亮了一会儿。我想记住的不是某个景点，而是大家同时安静下来的那几分钟。',['旅行','海风','摄影']),
 ('把一个小想法做出来','学习札记','最初只有一张纸上的三个方框。讨论时我们画了又擦，终于决定先把最小的一部分做出来。','晚上看到它第一次正常运行，所有人都笑了。进度条很短，但它确实向前走了一格。',['成长','项目','灵感']),
 ('旧书店里的意外发现','读书与摘记','那家书店藏在巷子最里面，门口堆着几盆叫不出名字的植物。店主让我们慢慢看，没有催促。','买到的书有一张陌生人的车票。我没有猜测完整的故事，只觉得人与人之间有时会留下很轻的回声。',['阅读','城市漫步']),
 ('秋天适合认真散步','生活片段','沿河的树开始变黄，我们没有定终点，只约好走累了就找地方坐下。路边的小狗认真嗅过每一片落叶。','今天聊了许多没有标准答案的问题。好在朋友不需要替彼此解答所有事情，愿意听就已经很好。',['秋日','朋友','散步']),
 ('山顶没有信号','旅行手记','最后一段坡路比预计的长。我们轮流提醒对方喝水，到了山顶才发现手机一直没有信号。','没有及时发出去的照片，后来成了最喜欢的一组。那天风很大，云影在山谷里移动，世界没有催促我们回复。',['旅行','徒步','摄影']),
 ('冬夜的一锅热汤','生活片段','回到屋里时手指还是凉的。锅盖掀开，白雾一下子模糊了眼镜，桌上的人开始互相递碗。','那一晚没有特别的安排，却让人觉得踏实。有些值得记住的日子，不需要发生大事。',['冬日','日常','家人']),
 ('星空下的十分钟','校园日记','操场的灯熄了几盏，我们抬头辨认那些讲过很多次、仍会认错的星座。云慢慢移开，大家同时发出一声轻叹。','照片里几乎什么也看不清，但我记得每个人的声音。记录有时候不是为了证明看见过，而是为了以后还能想起。',['校园','星空','朋友']),
 ('给未来的自己留一页','个人文集','整理旧笔记时，看见去年写下的一行计划。很多事情没有按想象发生，也有一些意外变得很好。','希望以后的我仍然愿意写下细小的感受，愿意承认犹豫，也愿意给每一次重新开始留出位置。',['成长','写作','回忆']),
 ('河边的风与归途','旅行手记','晚班车还要等二十分钟，我们沿着河堤慢慢走。对岸的灯一盏接一盏亮起来，水面像摊开了一封很长的信。','回程路上大家都困了，只剩窗外的树影向后退。旅行结束的时候，故事才开始有了可以反复讲述的形状。',['旅行','城市漫步','回忆']),
 ('不完美的第一盘饼干','生活片段','面团比想象中黏手，星星模具最后变成了不规则的小岛。烤箱响起时，我们挤在门口看颜色。','最好吃的一块并不是最好看的。今天学会了一件小事：给第一次尝试多一点耐心。',['日常','朋友','成长']),
]
backgrounds = sorted((Path(__file__).resolve().parents[1]/'northdiary/resources/backgrounds').glob('*.png'))
if not backgrounds:
    backgrounds = sorted((Path(__file__).resolve().parents[1]/'northdiary/resources/backgrounds').glob('*.jpg'))
keys=[]
for i in range(32):
    title,category,p1,p2,tags = stories[i%len(stories)]
    person_ids = rng.sample([p['id'] for p in persons], rng.randint(1,3))
    linked = [p for p in persons if p['id'] in person_ids]
    when = date(2023,1,12) + timedelta(days=int(i*43.5))
    diary = when.isoformat()
    if i in (4,17): diary=f'{when.year}-未知-未知'
    elif i in (9,23): diary=f'{when.year}-{when.month:02d}-未知'
    text = '\n\n'.join([p1, '同行的人：'+'、'.join(p['code'] for p in linked)+'。', p2,
        '记下一件小事：'+rng.choice(['路边的花开了。','今天的云像一封没有寄出的信。','终于把一直想做的事开始了。','我们约好下次还一起出发。']),
        '【NorthDiary 展示样例：文章、人物与经历均为虚构。】'])
    body=''.join('<p>'+html.escape(p)+'</p>' for p in text.split('\n\n'))
    article=repo.create(); keys.append(article.id)
    repo.save(article.id,title + (f' · 续记 {i//12}' if i>=12 else ''),diary,body,text,[category],tags,
              ['周末小记'] if i%6==0 else [],people=person_ids)
    if i%4==0 and backgrounds:
        for source in rng.sample(backgrounds,min(2,len(backgrounds))):
            attachments.add(article.id,source)
        for j,asset in enumerate(attachments.list(article.id)):
            caption=['途中风景','光影留念'][j]
            db.connection.execute('UPDATE attachments SET caption=?,position=? WHERE id=?',(caption,j,asset['id']))
            body+=f'<p><a href="ndiary-image:{asset["id"]}">▧ {caption} ↗</a></p>'
        db.connection.commit()
        repo.save(article.id,repo.get(article.id).title,diary,body,text,[category],tags,
                  ['周末小记'] if i%6==0 else [],people=person_ids)
    stamp=f'{when.isoformat()}T{9+i%10:02d}:{i%60:02d}:00+08:00'
    db.connection.execute('UPDATE articles SET created_at=?,updated_at=? WHERE id=?',(stamp,stamp,article.id))
    db.connection.commit()
    if i in (0,15,31):repo.set_pinned(article.id,True)
settings=QSettings(str(root/'ui.ini'),QSettings.Format.IniFormat)
settings.setValue('dark',True);settings.setValue('theme_name','dark');settings.setValue('season_background',True)
settings.setValue('article_sort','created_desc');settings.sync()
counts={t:db.connection.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['articles','people','tags','categories','relationship_tags','attachments']}
assert counts['articles']==32 and counts['people']==12
assert db.connection.execute('PRAGMA quick_check').fetchone()[0]=='ok'
assert not db.connection.execute('PRAGMA foreign_key_check').fetchall()
assert all((root/a[0]).is_file() for a in db.connection.execute('SELECT relative_path FROM attachments'))
db.close()
(root/'展示说明.txt').write_text('NorthDiary 虚构展示数据。与个人日记完全独立。\n配图使用软件自带季节背景素材。\n'+json.dumps(counts,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'data_dir':str(root),**counts},ensure_ascii=False))

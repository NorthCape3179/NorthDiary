package com.northcape.northdiary;

import android.app.AlertDialog;
import android.graphics.Typeface;
import android.text.*;
import android.text.method.LinkMovementMethod;
import android.text.style.StyleSpan;
import android.view.*;
import android.widget.*;
import java.util.*;
import static com.northcape.northdiary.Models.*;

/** Editing state is owned here and captured before lifecycle/navigation changes. */
final class EditorPanel extends ScrollView {
    private final MainActivity host;
    private final DiaryStore store;
    private final Article article;
    private final EditText title,date,tags,body;
    private final CheckBox outside,draft;
    private final TextView status,peopleLabel;
    private List<String> selectedPeople;
    private boolean bodyChanged;
    private final List<Attachment> attachments;
    EditorPanel(MainActivity host,DiaryStore store,Article article,boolean edit) {
        super(host);this.host=host;this.store=store;this.article=article;selectedPeople=new ArrayList<>(article.people);
        attachments=store.attachments(article.id);
        setFillViewport(true);LinearLayout content=Ui.column(host);Ui.pad(content,20);addView(content);
        LinearLayout actions=Ui.row(host);
        actions.addView(Ui.button(host,"返回",host::backFromArticle));
        if(article.deleted) actions.addView(Ui.button(host,"恢复文章",()->host.restoreArticle(article.id)));
        else {
            actions.addView(Ui.button(host,edit?"完成":"编辑",()->{if(edit)host.finishEditing();else host.editArticle(article);}));
            actions.addView(Ui.button(host,"移入回收站",()->host.trashArticle(article.id)));
        }
        content.addView(Ui.horizontal(host,actions));
        status=Ui.text(host,edit?"编辑中 · 停止输入后自动保存":"",13,R.color.muted);content.addView(status);
        title=Ui.input(host,"标题",true);title.setText(article.title);title.setTextSize(24);title.setTypeface(null,Typeface.BOLD);
        date=Ui.input(host,"事件日期：2026 / 2026-11 / 2026-11-01",true);date.setText(article.date.replace("-未知-未知","").replace("-未知",""));
        tags=Ui.input(host,"标签，用中文或英文逗号分隔",true);tags.setText(TextUtils.join("，",article.tags));
        outside=new CheckBox(host);outside.setText("时间线之外 · 阅读时隐藏事件日期");outside.setChecked(article.outside);
        draft=new CheckBox(host);draft.setText("待确认文章");draft.setChecked(article.draft);
        body=Ui.input(host,"写下想留下的记忆……",false);body.setGravity(Gravity.TOP);body.setMinLines(12);body.setTextSize(18);
        body.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        body.setText(ArticleText.parse(host,article.html,attachments));
        peopleLabel=Ui.text(host,"",14,R.color.accent);refreshPeople();
        if(edit) {
            content.addView(title);content.addView(outside);content.addView(date);date.setEnabled(!article.outside);
            content.addView(draft);content.addView(tags);content.addView(peopleLabel);
            content.addView(Ui.button(host,"选择关联人物",this::pickPeople));
            LinearLayout toolbar=Ui.row(host);
            toolbar.addView(Ui.button(host,"加粗",()->format(Typeface.BOLD)));
            toolbar.addView(Ui.button(host,"斜体",()->format(Typeface.ITALIC)));
            toolbar.addView(Ui.button(host,"添加图片链接",host::pickImage));content.addView(Ui.horizontal(host,toolbar));
            content.addView(Ui.text(host,"选中文字后设置格式。图片以文件名链接显示；点击下方附件链接可查看。",12,R.color.muted));
            content.addView(body);
            Ui.watch(title,host::editorChanged);Ui.watch(date,host::editorChanged);Ui.watch(tags,host::editorChanged);
            Ui.watch(body,()->{bodyChanged=true;host.editorChanged();});
            outside.setOnCheckedChangeListener((b,checked)->{date.setEnabled(!checked);host.editorChanged();});
            draft.setOnCheckedChangeListener((b,checked)->host.editorChanged());
        } else {
            content.addView(Ui.heading(host,article.title));
            if(!article.outside)content.addView(Ui.text(host,PartialDate.label(article.date),14,R.color.muted));
            if(!article.tags.isEmpty())content.addView(Ui.text(host,"标签："+TextUtils.join(" · ",article.tags),14,R.color.accent));
            content.addView(peopleLabel);
            TextView reader=Ui.text(host,"",18,R.color.ink);reader.setText(ArticleText.parse(host,article.html,attachments));
            reader.setLineSpacing(Ui.dp(host,5),1.1f);reader.setMovementMethod(LinkMovementMethod.getInstance());content.addView(reader);
        }
        if(!attachments.isEmpty()) {
            content.addView(Ui.text(host,"附件链接",14,R.color.muted));
            for(Attachment a:attachments) {
                TextView link=Ui.text(host,"↗ "+a.name,16,R.color.accent);
                link.setMinHeight(Ui.dp(host,48));link.setOnClickListener(v->ArticleText.open(host,"ndiary-image:"+a.id));content.addView(link);
            }
        }
    }
    Article capture() {
        article.title=title.getText().toString();article.date=date.getText().toString();
        article.outside=outside.isChecked();article.draft=draft.isChecked();
        article.tags=new ArrayList<>();for(String tag:tags.getText().toString().split("[,，\\n]"))if(!tag.trim().isEmpty())article.tags.add(tag.trim());
        article.people=new ArrayList<>(selectedPeople);
        if(bodyChanged) { article.html=Html.toHtml(body.getText(),Html.TO_HTML_PARAGRAPH_LINES_CONSECUTIVE);article.text=body.getText().toString(); }
        if(article.outside) {
            try{article.date=PartialDate.normalize(article.date);}catch(IllegalArgumentException e){article.date=java.time.LocalDate.now().toString();}
        }
        return article;
    }
    void status(String value){status.setText(value);}
    void insertAttachment(Attachment a) {
        int at=Math.max(0,body.getSelectionStart());SpannableString link=new SpannableString(a.name);
        link.setSpan(new ArticleText.ManagedLink("ndiary-image:"+a.id),0,link.length(),Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        body.getText().insert(at,link);bodyChanged=true;host.editorChanged();
    }
    private void format(int style) {
        int start=body.getSelectionStart(),end=body.getSelectionEnd();
        if(start<0||end<=start){Toast.makeText(host,"先选中要设置的文字",Toast.LENGTH_SHORT).show();return;}
        Editable text=body.getText();StyleSpan[] spans=text.getSpans(start,end,StyleSpan.class);boolean covered=false;
        for(StyleSpan span:spans)if(span.getStyle()==style&&text.getSpanStart(span)<=start&&text.getSpanEnd(span)>=end)covered=true;
        for(StyleSpan span:spans)if(span.getStyle()==style) {
            int left=text.getSpanStart(span),right=text.getSpanEnd(span);text.removeSpan(span);
            if(left<start)text.setSpan(new StyleSpan(style),left,start,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            if(right>end)text.setSpan(new StyleSpan(style),end,right,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        if(!covered)text.setSpan(new StyleSpan(style),start,end,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        bodyChanged=true;host.editorChanged();
    }
    private void pickPeople() {
        List<Person> list=store.people("");String[] names=new String[list.size()];boolean[] checked=new boolean[list.size()];
        for(int i=0;i<list.size();i++){names[i]=list.get(i).name+"（"+list.get(i).code+"）";checked[i]=selectedPeople.contains(list.get(i).id);}
        new AlertDialog.Builder(host).setTitle("关联人物").setMultiChoiceItems(names,checked,(d,i,yes)->checked[i]=yes)
            .setPositiveButton("确定",(d,w)->{selectedPeople.clear();for(int i=0;i<list.size();i++)if(checked[i])selectedPeople.add(list.get(i).id);refreshPeople();host.editorChanged();})
            .setNegativeButton("取消",null).show();
    }
    private void refreshPeople() {
        List<String> names=new ArrayList<>();for(Person p:store.people(""))if(selectedPeople.contains(p.id))names.add(p.name);
        peopleLabel.setText(names.isEmpty()?"未关联人物":"人物："+TextUtils.join(" · ",names));
    }
}

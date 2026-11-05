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
    private final EditText title,date,tags,categories,body;
    private final CheckBox outside,draft;
    private final TextView status,peopleLabel;
    private List<String> selectedPeople;
    private boolean bodyChanged;
    private boolean indentEnabled;
    private final List<Attachment> attachments;
    EditorPanel(MainActivity host,DiaryStore store,Article article,boolean edit) {
        super(host);setTag("article-reader");this.host=host;this.store=store;this.article=article;selectedPeople=new ArrayList<>(article.people);
        attachments=store.attachments(article.id);
        setFillViewport(true);setVerticalScrollBarEnabled(false);LinearLayout content=Ui.column(host);Ui.pad(content,20);addView(content);
        LinearLayout actions=Ui.row(host);
        actions.addView(Ui.quiet(host,"‹ 返回",host::backFromArticle));
        View spacer=new View(host);actions.addView(spacer,new LinearLayout.LayoutParams(0,1,1));
        if(article.deleted) actions.addView(Ui.button(host,"恢复文章",()->host.restoreArticle(article.id)));
        else {
            Button more=Ui.quiet(host,"更多",()->new AlertDialog.Builder(host).setItems(new String[]{"移入回收站"},(d,i)->host.trashArticle(article.id)).show());actions.addView(more);
            actions.addView(Ui.primary(host,edit?"完成":"编辑",()->{if(edit)host.finishEditing();else host.editArticle(article);}));
        }
        for(int i=0;i<actions.getChildCount()-1;i++){
            LinearLayout.LayoutParams p=(LinearLayout.LayoutParams)actions.getChildAt(i).getLayoutParams();p.rightMargin=Ui.dp(host,6);actions.getChildAt(i).setLayoutParams(p);
        }
        content.addView(actions);Ui.gap(content,12);
        status=Ui.text(host,edit?"本地草稿 · 自动保存":"私人记忆 · 只读浏览",11,R.color.muted);content.addView(status);Ui.gap(content,14);
        title=Ui.input(host,"标题",true);title.setText(article.title);title.setTextSize(26);title.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));title.setBackground(null);title.setPadding(0,Ui.dp(host,8),0,Ui.dp(host,12));
        date=Ui.input(host,"事件日期：2026 / 2026-11 / 2026-11-01",true);date.setText(article.date.replace("-未知-未知","").replace("-未知",""));
        tags=Ui.input(host,"标签，用中文或英文逗号分隔",true);tags.setText(TextUtils.join("，",article.tags));
        categories=Ui.input(host,"分类，用中文或英文逗号分隔",true);categories.setText(article.categories==null?"":TextUtils.join("，",article.categories));
        outside=new CheckBox(host);outside.setText("时间线之外 · 阅读时隐藏事件日期");outside.setChecked(article.outside);
        draft=new CheckBox(host);draft.setText("待确认文章");draft.setChecked(article.draft);
        body=Ui.input(host,"写下想留下的记忆……",false);body.setGravity(Gravity.TOP);body.setMinLines(12);body.setTextSize(17);body.setBackground(null);body.setPadding(0,Ui.dp(host,8),0,Ui.dp(host,20));body.setLineSpacing(Ui.dp(host,6),1.1f);
        body.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        body.setText(ArticleText.parse(host,article.html,attachments));
        indentEnabled=host.getSharedPreferences("editor",0).getBoolean("autoIndent",true);
        if(edit)ParagraphFormatting.autoIndent(body.getText(),indentEnabled,ParagraphFormatting.indentWidth(host));
        peopleLabel=Ui.text(host,"",14,R.color.accent);refreshPeople();
        if(edit) {
            content.addView(title);
            LinearLayout meta=Ui.column(host);Ui.card(meta);meta.setVisibility(GONE);
            Button organize=Ui.button(host,"日期、分类、标签与人物  ⌄",()->meta.setVisibility(meta.getVisibility()==GONE?VISIBLE:GONE));content.addView(organize);Ui.gap(content,10);content.addView(meta);
            meta.addView(outside);Ui.gap(meta,8);meta.addView(Ui.text(host,"事件日期",12,R.color.muted));Ui.gap(meta,6);meta.addView(date);date.setEnabled(!article.outside);
            Ui.gap(meta,8);meta.addView(draft);Ui.gap(meta,8);meta.addView(Ui.text(host,"分类",12,R.color.muted));Ui.gap(meta,6);meta.addView(categories);
            Ui.gap(meta,8);meta.addView(Ui.text(host,"标签",12,R.color.muted));Ui.gap(meta,6);meta.addView(tags);Ui.gap(meta,12);meta.addView(peopleLabel);Ui.gap(meta,8);
            meta.addView(Ui.button(host,"选择关联人物",this::pickPeople));Ui.gap(content,16);
            LinearLayout toolbar=Ui.row(host);
            toolbar.addView(Ui.button(host,"加粗",()->format(Typeface.BOLD)));
            toolbar.addView(Ui.button(host,"斜体",()->format(Typeface.ITALIC)));
            toolbar.addView(Ui.button(host,"居中",()->{
                ParagraphFormatting.toggleCenter(body.getText(),Math.max(0,body.getSelectionStart()),Math.max(0,body.getSelectionEnd()),indentEnabled,ParagraphFormatting.indentWidth(host));bodyChanged=true;host.editorChanged();
            }));
            toolbar.addView(Ui.button(host,"添加图片链接",host::pickImage));
            toolbar.addView(Ui.button(host,"自动缩进",()->{
                indentEnabled=!indentEnabled;host.getSharedPreferences("editor",0).edit().putBoolean("autoIndent",indentEnabled).apply();
                ParagraphFormatting.autoIndent(body.getText(),indentEnabled,ParagraphFormatting.indentWidth(host));bodyChanged=true;host.editorChanged();
                Toast.makeText(host,indentEnabled?"已开启自动首行缩进（两字宽）":"已关闭自动首行缩进",Toast.LENGTH_SHORT).show();
            }));
            for(int i=0;i<toolbar.getChildCount()-1;i++){
                LinearLayout.LayoutParams p=(LinearLayout.LayoutParams)toolbar.getChildAt(i).getLayoutParams();p.rightMargin=Ui.dp(host,8);toolbar.getChildAt(i).setLayoutParams(p);
            }
            content.addView(Ui.horizontal(host,toolbar));
            Ui.gap(content,10);content.addView(body);
            content.addView(Ui.text(host,"选中文字后设置格式。图片以文件名链接保存在文章中。",11,R.color.muted));Ui.gap(content,12);
            Ui.watch(title,host::editorChanged);Ui.watch(date,host::editorChanged);Ui.watch(tags,host::editorChanged);Ui.watch(categories,host::editorChanged);
            body.addTextChangedListener(new TextWatcher(){
                public void beforeTextChanged(CharSequence s,int start,int count,int after){}
                public void onTextChanged(CharSequence s,int start,int before,int count){bodyChanged=true;host.editorChanged();}
                public void afterTextChanged(Editable text){ParagraphFormatting.autoIndent(text,indentEnabled,ParagraphFormatting.indentWidth(host));}
            });
            outside.setOnCheckedChangeListener((b,checked)->{date.setEnabled(!checked);host.editorChanged();});
            draft.setOnCheckedChangeListener((b,checked)->host.editorChanged());
        } else {
            TextView heading=Ui.heading(host,article.title);heading.setTextSize(27);content.addView(heading);Ui.gap(content,12);
            if(!article.outside)content.addView(Ui.text(host,PartialDate.label(article.date),14,R.color.muted));
            if(!article.tags.isEmpty())content.addView(Ui.text(host,"标签："+TextUtils.join(" · ",article.tags),14,R.color.accent));
            if(article.categories!=null&&!article.categories.isEmpty())content.addView(Ui.text(host,"分类："+TextUtils.join(" · ",article.categories),14,R.color.accent));
            if(!selectedPeople.isEmpty()){Ui.gap(content,10);content.addView(peopleLabel);}Ui.gap(content,22);
            TextView reader=Ui.text(host,"",18,R.color.ink);reader.setText(ArticleText.parse(host,article.html,attachments));
            reader.setLineSpacing(Ui.dp(host,5),1.1f);reader.setMovementMethod(LinkMovementMethod.getInstance());content.addView(reader);
        }
        if(!attachments.isEmpty()) {
            Ui.section(content,"附件链接");
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
        article.categories=new ArrayList<>();for(String name:categories.getText().toString().split("[,，\\n]"))if(!name.trim().isEmpty())article.categories.add(name.trim());
        article.people=new ArrayList<>(selectedPeople);
        if(bodyChanged) { article.html=ParagraphFormatting.html(body.getText());article.text=body.getText().toString(); }
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

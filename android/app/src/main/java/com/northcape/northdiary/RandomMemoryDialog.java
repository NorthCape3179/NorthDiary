package com.northcape.northdiary;

import android.app.AlertDialog;
import android.text.method.LinkMovementMethod;
import android.widget.*;
import java.util.*;
import static com.northcape.northdiary.Models.*;

/** Preview is read-only; drawing another memory never updates an article timestamp. */
final class RandomMemoryDialog extends AlertDialog {
    private final MainActivity host;
    private final DiaryStore store;
    private final List<Article> articles;
    private final TextView title,date,body;
    private final LinearLayout links;
    private final ScrollView scroll;
    private Article current;
    RandomMemoryDialog(MainActivity host,DiaryStore store){
        super(host);this.host=host;this.store=store;articles=store.exportable();setTitle("随机回忆");
        LinearLayout content=Ui.column(host);Ui.pad(content,20);content.setBackgroundColor(Ui.color(host,R.color.card));
        content.addView(Ui.text(host,"从有日期与时间线之外的已确认文章中抽取",12,R.color.muted));Ui.gap(content,12);
        title=Ui.heading(host,"");content.addView(title);date=Ui.text(host,"",12,R.color.accent);content.addView(date);Ui.gap(content,16);
        body=Ui.text(host,"",17,R.color.ink);body.setLineSpacing(Ui.dp(host,5),1.1f);body.setMovementMethod(LinkMovementMethod.getInstance());content.addView(body);
        links=Ui.column(host);content.addView(links);scroll=new ScrollView(host);scroll.addView(content);setView(scroll);
        setButton(BUTTON_NEGATIVE,"关闭",(d,w)->dismiss());setButton(BUTTON_NEUTRAL,"再来一篇",(d,w)->{});setButton(BUTTON_POSITIVE,"打开文章",(d,w)->{});
        setOnShowListener(d->{getButton(BUTTON_NEUTRAL).setOnClickListener(v->draw());getButton(BUTTON_POSITIVE).setOnClickListener(v->{if(current!=null){dismiss();host.openArticle(current.id,false);}});draw();});
    }
    static Article pick(List<Article> articles,String previous,Random random){
        List<Article> eligible=new ArrayList<>();for(Article a:articles)if(!a.deleted&&!a.draft)eligible.add(a);
        if(eligible.size()>1)eligible.removeIf(a->a.id.equals(previous));
        return eligible.isEmpty()?null:eligible.get(random.nextInt(eligible.size()));
    }
    private void draw(){
        current=pick(articles,host.lastRandomId,new Random());links.removeAllViews();scroll.scrollTo(0,0);
        if(current==null){title.setText("还没有可抽取的回忆");date.setText("");body.setText("确认第一篇文章后，再来看看。");getButton(BUTTON_NEUTRAL).setEnabled(false);getButton(BUTTON_POSITIVE).setEnabled(false);return;}
        host.lastRandomId=current.id;title.setText(current.title);date.setText(current.outside?"时间线之外":PartialDate.label(current.date));
        List<Attachment> attachments=store.attachments(current.id);body.setText(ArticleText.parse(host,current.html,attachments));
        for(Attachment a:attachments){Ui.gap(links,8);links.addView(Ui.quiet(host,"↗ "+a.name,()->ArticleText.open(host,"ndiary-image:"+a.id)));}
    }
}

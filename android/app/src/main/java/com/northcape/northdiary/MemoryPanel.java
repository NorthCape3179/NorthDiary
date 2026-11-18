package com.northcape.northdiary;

import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.text.TextUtils;
import android.view.*;
import android.widget.*;
import java.util.*;
import static com.northcape.northdiary.Models.*;

/** Search and space controls stay in place while the virtualized list refreshes. */
final class MemoryPanel extends LinearLayout {
    private final MainActivity host;
    private final DiaryStore store;
    private final ListView list;
    private final LinearLayout spaces;
    private final TextView count;
    private final Button sort;
    private List<Article> articles=new ArrayList<>();
    MemoryPanel(MainActivity host,DiaryStore store){
        super(host);this.host=host;this.store=store;setOrientation(VERTICAL);setPadding(Ui.dp(host,20),Ui.dp(host,8),Ui.dp(host,20),0);
        LinearLayout title=Ui.row(host);LinearLayout labels=Ui.column(host);labels.addView(Ui.heading(host,"记忆档案"));
        if(!Ui.compact(host)){Ui.gap(labels,5);labels.addView(Ui.text(host,"让零散的往事，有处可寻。",12,R.color.muted));}
        title.addView(labels,new LayoutParams(0,-2,1));title.addView(Ui.primary(host,"＋ 新建",host::newArticle));addView(title);Ui.gap(this,Ui.compact(host)?10:20);
        EditText query=Ui.search(host,"搜索标题和正文");query.setText(host.query);addView(query);Ui.gap(this,12);
        spaces=Ui.row(host);addView(Ui.horizontal(host,spaces));renderSpaces();Ui.gap(this,10);
        LinearLayout filters=Ui.row(host);Button tag=Ui.quiet(host,host.tag.isEmpty()?"全部标签 ⌄":host.tag+" ⌄",host::pickTag);tag.setTextSize(12);Ui.weighted(filters,tag,1);
        sort=Ui.quiet(host,"",()->{host.byDate=!host.byDate;refresh();});sort.setTextSize(12);Ui.weighted(filters,sort,1);addView(filters);
        LinearLayout tools=Ui.row(host);Button category=Ui.quiet(host,host.category.isEmpty()?"全部分类 ⌄":host.category+" ⌄",host::pickCategory);category.setSingleLine(true);category.setTextSize(12);Ui.weighted(tools,category,1.2f);
        Button random=Ui.quiet(host,"随机回忆",host::randomMemory),export=Ui.quiet(host,"导出文集",host::exportEpub);random.setTextSize(12);export.setTextSize(12);random.setSingleLine(true);export.setSingleLine(true);Ui.weighted(tools,random,1);Ui.weighted(tools,export,1);addView(tools);
        count=Ui.text(host,"",11,R.color.muted);count.setPadding(Ui.dp(host,4),Ui.dp(host,8),0,Ui.dp(host,10));if(!Ui.compact(host))addView(count);
        FrameLayout body=new FrameLayout(host);addView(body,new LayoutParams(-1,0,1));
        list=new ListView(host);list.setDivider(new ColorDrawable(android.graphics.Color.TRANSPARENT));list.setDividerHeight(Ui.dp(host,10));list.setVerticalScrollBarEnabled(false);list.setClipToPadding(false);list.setPadding(0,0,0,Ui.dp(host,10));body.addView(list,new FrameLayout.LayoutParams(-1,-1));
        View empty=Ui.empty(host,"这一页，等你写下","文字、人物与照片链接，\n都可以成为回忆的入口。","写下第一篇",host::newArticle);body.addView(empty,new FrameLayout.LayoutParams(-1,-1));list.setEmptyView(empty);
        list.setOnItemClickListener((p,v,i,id)->host.openArticle(articles.get(i).id,false));
        Ui.watch(query,()->{host.query=query.getText().toString();refresh();});refresh();
    }
    private void renderSpaces(){
        spaces.removeAllViews();String[] names={"有日期","时间线之外","待确认","回收站"};
        for(int i=0;i<names.length;i++){
            final int selected=i;TextView chip=Ui.text(host,names[i],12,i==host.space?R.color.on_accent:R.color.muted);chip.setGravity(Gravity.CENTER);chip.setMinHeight(Ui.dp(host,40));chip.setPadding(Ui.dp(host,13),Ui.dp(host,9),Ui.dp(host,13),Ui.dp(host,9));
            chip.setBackground(Ui.ripple(host,i==host.space?R.color.accent:R.color.paper,13,false));chip.setSelected(i==host.space);chip.setFocusable(true);
            chip.setOnClickListener(v->{host.space=selected;renderSpaces();refresh();});LayoutParams p=new LayoutParams(-2,-2);p.setMargins(0,0,Ui.dp(host,5),0);spaces.addView(chip,p);
        }
    }
    void refresh(){
        articles=store.list(host.query,host.tag,host.category,host.space,host.byDate,null);count.setText(articles.size()+" 篇记忆");sort.setText(host.byDate?"事件时间 ↓":"创建时间 ↓");
        list.setAdapter(new BaseAdapter(){
            public int getCount(){return articles.size();}public Article getItem(int i){return articles.get(i);}public long getItemId(int i){return i;}
            public View getView(int i,View recycled,ViewGroup parent){
                Article a=getItem(i);LinearLayout card=Ui.column(host);Ui.card(card);
                String date=host.space==1?"时间线之外":PartialDate.label(a.date);TextView meta=Ui.text(host,date,11,R.color.accent);meta.setLetterSpacing(.04f);card.addView(meta);Ui.gap(card,9);
                TextView title=Ui.text(host,a.title,18,R.color.ink);title.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));title.setMaxLines(2);title.setEllipsize(TextUtils.TruncateAt.END);card.addView(title);Ui.gap(card,8);
                TextView summary=Ui.text(host,a.text.isEmpty()?"一段尚未写完的记忆":a.text.replace('\n',' '),13,R.color.muted);summary.setMaxLines(2);summary.setEllipsize(TextUtils.TruncateAt.END);card.addView(summary);
                return card;
            }
        });
    }
}

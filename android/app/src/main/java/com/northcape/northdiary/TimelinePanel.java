package com.northcape.northdiary;

import android.app.AlertDialog;
import android.graphics.*;
import android.graphics.drawable.ColorDrawable;
import android.text.TextUtils;
import android.view.*;
import android.widget.*;
import java.util.*;
import static com.northcape.northdiary.TimelineEntries.*;

/** A virtualized, touch-friendly timeline, continuous through year/month/event rows. */
final class TimelinePanel extends LinearLayout {
    private final MainActivity host;
    private final List<Entry> entries;
    private final ListView list;
    TimelinePanel(MainActivity host,DiaryStore store,String selectedId){
        super(host);this.host=host;setOrientation(VERTICAL);setPadding(Ui.dp(host,20),Ui.dp(host,8),Ui.dp(host,20),0);
        entries=TimelineEntries.build(store.list("","",0,true,null));
        LinearLayout top=Ui.row(host);top.addView(Ui.heading(host,"时间线"),new LayoutParams(0,-2,1));top.addView(Ui.primary(host,"＋ 新建",host::newArticle));addView(top);
        Ui.gap(this,6);addView(Ui.text(host,"沿着时间，重访记忆。",13,R.color.muted));Ui.gap(this,Ui.compact(host)?8:18);
        LinearLayout tools=Ui.row(host);Ui.weighted(tools,Ui.button(host,"跳到年份 ⌄",this::jumpYear),1);Ui.weighted(tools,Ui.quiet(host,"回到最近 ↑",()->goTo(0)),1);addView(tools);Ui.gap(this,10);
        int articles=0;for(Entry e:entries)if(e.kind==Kind.ARTICLE)articles++;
        if(!Ui.compact(host)){addView(Ui.text(host,articles+" 篇回忆 · 从近到远",11,R.color.muted));Ui.gap(this,8);}
        FrameLayout body=new FrameLayout(host);addView(body,new LayoutParams(-1,0,1));
        list=new ListView(host);list.setDivider(new ColorDrawable(Color.TRANSPARENT));list.setDividerHeight(0);list.setVerticalScrollBarEnabled(false);list.setClipToPadding(false);list.setPadding(0,0,0,Ui.dp(host,16));
        list.setAdapter(new BaseAdapter(){
            public int getCount(){return entries.size();}public Entry getItem(int i){return entries.get(i);}public long getItemId(int i){return i;}
            // Keep headers selectable so non-touch devices do not scroll past them on entry.
            // The click listener opens article rows only.
            @Override public boolean areAllItemsEnabled(){return true;}
            @Override public boolean isEnabled(int position){return true;}
            @Override public int getViewTypeCount(){return 3;}
            @Override public int getItemViewType(int position){return getItem(position).kind.ordinal();}
            public View getView(int position,View old,ViewGroup parent){return entryView(getItem(position),selectedId);}
        });
        body.addView(list,new FrameLayout.LayoutParams(-1,-1));
        View empty=Ui.empty(host,"让回忆，连成一条线","确认后的有日期文章会出现在这里。\n时间线之外，仍有自己的位置。","写一篇回忆",host::newArticle);
        body.addView(empty,new FrameLayout.LayoutParams(-1,-1));list.setEmptyView(empty);
        list.setOnItemClickListener((parent,view,index,id)->{Entry entry=entries.get(index);if(entry.article!=null)host.openArticle(entry.article.id,false);});
        if(!entries.isEmpty())list.setSelectionFromTop(Math.min(host.timelineIndex,entries.size()-1),host.timelineOffset);
        list.setOnScrollListener(new AbsListView.OnScrollListener(){
            public void onScrollStateChanged(AbsListView v,int state){}
            public void onScroll(AbsListView v,int first,int visible,int total){
                if(v.getChildCount()>0){host.timelineIndex=first;host.timelineOffset=v.getChildAt(0).getTop();}
            }
        });
    }
    private View entryView(Entry entry,String selectedId){
        LinearLayout row=Ui.row(host);row.setGravity(Gravity.TOP);
        Rail rail=new Rail(entry.kind,entry.article!=null&&entry.article.id.equals(selectedId));
        row.addView(rail,new LayoutParams(Ui.dp(host,30),-1));
        if(entry.kind==Kind.YEAR){
            LinearLayout labels=Ui.row(host);labels.setPadding(Ui.dp(host,8),Ui.dp(host,14),0,Ui.dp(host,14));
            TextView year=Ui.heading(host,entry.label);year.setTextColor(Ui.color(host,R.color.accent));labels.addView(year);
            TextView count=Ui.text(host,"  ·  "+entry.count+" 篇",11,R.color.muted);labels.addView(count);row.addView(labels,new LayoutParams(0,-2,1));
        }else if(entry.kind==Kind.MONTH){
            LinearLayout labels=Ui.row(host);labels.setPadding(Ui.dp(host,8),Ui.dp(host,12),0,Ui.dp(host,12));
            TextView month=Ui.text(host,entry.label,15,R.color.ink);month.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));labels.addView(month);
            labels.addView(Ui.text(host,"  /  "+entry.count+" 篇回忆",11,R.color.muted));row.addView(labels,new LayoutParams(0,-2,1));
        }else{
            LinearLayout card=Ui.column(host);Ui.card(card);boolean selected=entry.article.id.equals(selectedId);
            if(selected)card.setBackground(Ui.surface(host,R.color.soft,20,true));
            card.addView(Ui.text(host,entry.label,11,R.color.accent));Ui.gap(card,8);
            TextView title=Ui.text(host,entry.article.title,17,R.color.ink);title.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));title.setMaxLines(2);title.setEllipsize(TextUtils.TruncateAt.END);card.addView(title);
            if(!entry.article.text.isEmpty()){
                Ui.gap(card,7);TextView summary=Ui.text(host,entry.article.text.replace('\n',' '),12,R.color.muted);summary.setMaxLines(2);summary.setEllipsize(TextUtils.TruncateAt.END);card.addView(summary);
            }
            LayoutParams p=new LayoutParams(0,-2,1);p.setMargins(Ui.dp(host,8),0,0,Ui.dp(host,12));row.addView(card,p);
        }
        return row;
    }
    private void goTo(int position){if(!entries.isEmpty())list.setSelectionFromTop(position,0);}
    private void jumpYear(){
        List<String> years=new ArrayList<>();List<Integer> positions=new ArrayList<>();
        for(int i=0;i<entries.size();i++)if(entries.get(i).kind==Kind.YEAR){years.add(entries.get(i).label);positions.add(i);}
        if(years.isEmpty()){Toast.makeText(host,"有回忆后，就可以按年份跳转。",Toast.LENGTH_SHORT).show();return;}
        new AlertDialog.Builder(host).setTitle("跳到年份").setItems(years.toArray(new String[0]),(d,index)->goTo(positions.get(index))).setNegativeButton("取消",null).show();
    }
    private final class Rail extends View {
        private final Kind kind;private final boolean selected;private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        Rail(Kind kind,boolean selected){super(host);this.kind=kind;this.selected=selected;setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
        @Override protected void onDraw(Canvas canvas){
            float x=Ui.dp(host,13),y=Ui.dp(host,kind==Kind.YEAR?31:kind==Kind.MONTH?23:26);
            paint.setColor(Ui.color(host,R.color.line));paint.setStrokeWidth(Ui.dp(host,1.5f));canvas.drawLine(x,0,x,getHeight(),paint);
            float radius=Ui.dp(host,kind==Kind.YEAR?6:selected?5:3.5f);paint.setColor(Ui.color(host,R.color.paper));canvas.drawCircle(x,y,radius+Ui.dp(host,3),paint);
            paint.setColor(Ui.color(host,kind==Kind.MONTH?R.color.muted:R.color.accent));canvas.drawCircle(x,y,radius,paint);
        }
    }
}

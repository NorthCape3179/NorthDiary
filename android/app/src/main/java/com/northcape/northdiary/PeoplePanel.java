package com.northcape.northdiary;

import android.app.AlertDialog;
import android.view.*;
import android.widget.*;
import java.util.*;
import static com.northcape.northdiary.Models.*;

final class PeoplePanel extends LinearLayout {
    private final MainActivity host;
    private final DiaryStore store;
    private final GridView list;
    private final EditText search;
    private List<Person> people=new ArrayList<>();
    PeoplePanel(MainActivity host,DiaryStore store) {
        super(host);this.host=host;this.store=store;setOrientation(VERTICAL);Ui.pad(this,20);
        LinearLayout top=Ui.row(host);top.addView(Ui.heading(host,"人物档案"),new LayoutParams(0,-2,1));top.addView(Ui.primary(host,"＋ 新建",()->edit(null)));addView(top);
        Ui.gap(this,6);addView(Ui.text(host,"有些故事，从一个名字开始。",13,R.color.muted));Ui.gap(this,20);
        search=Ui.search(host,"搜索姓名或代号");addView(search);Ui.gap(this,18);
        list=new GridView(host);list.setNumColumns(Math.max(1,Math.min(4,host.getResources().getConfiguration().screenWidthDp/180)));
        list.setHorizontalSpacing(Ui.dp(host,14));list.setVerticalSpacing(Ui.dp(host,14));list.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);list.setVerticalScrollBarEnabled(false);addView(list,new LayoutParams(-1,0,1));
        Ui.watch(search,this::refresh);list.setOnItemClickListener((p,v,i,id)->detail(people.get(i)));refresh();
    }
    private void refresh() {
        people=store.people(search.getText().toString());
        list.setAdapter(new BaseAdapter(){
            public int getCount(){return people.size();}public Person getItem(int i){return people.get(i);}public long getItemId(int i){return i;}
            public View getView(int i,View old,ViewGroup parent){
                Person p=getItem(i);LinearLayout card=Ui.column(host);Ui.card(card);card.setGravity(Gravity.CENTER);
                TextView avatar=Ui.text(host,p.name.isEmpty()?"人":p.name.substring(0,p.name.offsetByCodePoints(0,1)),22,R.color.accent);avatar.setGravity(Gravity.CENTER);avatar.setBackground(Ui.surface(host,R.color.soft,32,false));
                card.addView(avatar,new LayoutParams(Ui.dp(host,60),Ui.dp(host,60)));Ui.gap(card,14);
                TextView name=Ui.text(host,p.name,18,R.color.ink);name.setMaxLines(1);name.setEllipsize(android.text.TextUtils.TruncateAt.END);card.addView(name);Ui.gap(card,6);card.addView(Ui.text(host,p.code,12,R.color.muted));Ui.gap(card,4);return card;
            }
        });
        TextView empty=Ui.text(host,"还没有人物档案，点击上方新建。",16,R.color.muted);
        if(list.getEmptyView()!=null)removeView(list.getEmptyView());addView(empty);list.setEmptyView(empty);
    }
    private void detail(Person p) {
        LinearLayout page=Ui.column(host);Ui.pad(page,20);
        page.addView(Ui.heading(host,"◯  "+p.name));page.addView(Ui.text(host,"代号："+p.code,16,R.color.accent));
        page.addView(Ui.text(host,"出生："+(p.birth.isEmpty()?"未填写":PartialDate.label(p.birth))+"\n相遇："+(p.met.isEmpty()?"未填写":PartialDate.label(p.met))+"\n"+p.how,16,R.color.ink));
        page.addView(Ui.button(host,"编辑资料",()->edit(p)));
        page.addView(Ui.text(host,"相关回忆（含时间线之外和待确认）",14,R.color.muted));
        AlertDialog dialog=new AlertDialog.Builder(host).setView(Ui.scroll(host,page)).setPositiveButton("关闭",null).create();
        for(int space=0;space<3;space++)for(Article a:store.list("","",space,false,p.id)) {
            Button link=Ui.button(host,a.title,()->{dialog.dismiss();host.openArticle(a.id,false);});page.addView(link);
        }
        page.addView(Ui.button(host,"删除人物",()->new AlertDialog.Builder(host).setMessage("删除人物档案并解除关联？文章会保留。")
            .setPositiveButton("删除",(d,w)->{try{store.deletePerson(p.id);dialog.dismiss();refresh();}catch(Exception e){Ui.error(host,e);}}).setNegativeButton("取消",null).show()));
        dialog.show();
    }
    private void edit(Person original) {
        Person p=new Person();p.id=original==null?UUID.randomUUID().toString():original.id;
        LinearLayout form=Ui.column(host);Ui.pad(form,20);
        String[] hints={"姓名（必填）","代号（必填且唯一）","出生日期，可留空","相遇日期，可留空","相遇方式 / 简介"};
        String[] values=original==null?new String[]{"","","","",""}:new String[]{original.name,original.code,original.birth,original.met,original.how};
        EditText[] fields=new EditText[5];for(int i=0;i<5;i++){fields[i]=Ui.input(host,hints[i],i!=4);fields[i].setText(values[i]);form.addView(fields[i]);}
        form.addView(Ui.text(host,"日期支持 YYYY、YYYY-MM、YYYY-MM-DD。",12,R.color.muted));
        AlertDialog dialog=new AlertDialog.Builder(host).setTitle(original==null?"新建人物":"编辑人物").setView(Ui.scroll(host,form))
            .setPositiveButton("保存",null).setNegativeButton("取消",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            try {
                p.name=fields[0].getText().toString();p.code=fields[1].getText().toString();p.birth=fields[2].getText().toString().trim();
                p.met=fields[3].getText().toString().trim();p.how=fields[4].getText().toString();store.savePerson(p);dialog.dismiss();refresh();
                if(original!=null){original.name=p.name;original.code=p.code;original.birth=p.birth;original.met=p.met;original.how=p.how;}
            }catch(Exception e){Ui.error(host,e);}
        }));dialog.show();
    }
}

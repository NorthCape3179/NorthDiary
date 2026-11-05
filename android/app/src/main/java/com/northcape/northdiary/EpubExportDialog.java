package com.northcape.northdiary;

import android.app.*;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
import java.util.*;
import static com.northcape.northdiary.Models.*;

/** Checks are independent of row order; group actions replace the checked set. */
final class EpubExportDialog extends Dialog {
    private final MainActivity host;
    private final List<Article> rows;
    private final Set<String> selected=new LinkedHashSet<>();
    private final Map<String,Set<String>> categories=new TreeMap<>(),tags=new TreeMap<>();
    private final Bundle restored;
    private EditText title,author;
    private ListView list;
    private ScrollView controls;
    private TextView count,error;
    AlertDialog groupDialog;
    EpubExportDialog(MainActivity host,DiaryStore store,Bundle restored){
        super(host,Appearance.choice(host).equals("forest")?R.style.ForestTheme:R.style.AppTheme);this.host=host;this.restored=restored;rows=store.exportable();
        if(restored!=null){
            ArrayList<String> order=restored.getStringArrayList("order");
            if(order!=null){Map<String,Integer> positions=new HashMap<>();for(int i=0;i<order.size();i++)positions.put(order.get(i),i);rows.sort(Comparator.comparingInt(a->positions.getOrDefault(a.id,Integer.MAX_VALUE)));}
        }
        ArrayList<String> saved=restored==null?null:restored.getStringArrayList("selected");
        for(Article a:rows){
            if(saved==null||saved.contains(a.id))selected.add(a.id);
            if(a.categories!=null)for(String name:a.categories)categories.computeIfAbsent(name,key->new LinkedHashSet<>()).add(a.id);
            for(String name:store.articleTags(a.id))tags.computeIfAbsent(name,key->new LinkedHashSet<>()).add(a.id);
        }
    }
    @Override protected void onCreate(Bundle state){
        super.onCreate(state);getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE|WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
        LinearLayout content=Ui.column(host);Ui.pad(content,20);content.setBackgroundColor(Ui.color(host,R.color.card));content.setFocusableInTouchMode(true);
        LinearLayout form=Ui.column(host);controls=new ScrollView(host);controls.setFillViewport(false);controls.addView(form);content.addView(controls,new LinearLayout.LayoutParams(-1,Ui.dp(host,280)));
        form.addView(Ui.heading(host,"导出文集"));Ui.gap(form,8);
        form.addView(Ui.text(host,"包含两个空间的已确认文章。生成阅读用电子书；完整恢复请使用 .ndiary 备份。",12,R.color.muted));Ui.gap(form,12);
        title=Ui.input(host,"书名",true);title.setTag("epub-title");title.setText(restored==null?"NorthDiary 文集":restored.getString("title","NorthDiary 文集"));form.addView(title);Ui.gap(form,8);
        author=Ui.input(host,"作者（选填）",true);author.setText(restored==null?"":restored.getString("author",""));form.addView(author);Ui.gap(form,8);
        LinearLayout groups=Ui.row(host);
        Button category=Ui.quiet(host,"按分类选择",()->chooseGroup("分类",categories));category.setEnabled(!categories.isEmpty());Ui.weighted(groups,category,1);
        Button tag=Ui.quiet(host,"按标签选择",()->chooseGroup("标签",tags));tag.setEnabled(!tags.isEmpty());Ui.weighted(groups,tag,1);form.addView(groups);
        LinearLayout actions=Ui.row(host);Ui.weighted(actions,Ui.quiet(host,"全选",()->select(null)),1);Ui.weighted(actions,Ui.quiet(host,"取消全选",()->select(Collections.emptySet())),1);form.addView(actions);
        form.addView(Ui.text(host,"按分类或标签选择会替换勾选。长按章节可上下移动。",11,R.color.muted));
        count=Ui.text(host,"",12,R.color.accent);count.setPadding(0,Ui.dp(host,8),0,Ui.dp(host,8));content.addView(count);
        list=new ListView(host);list.setTag("epub-chapters");list.setChoiceMode(ListView.CHOICE_MODE_MULTIPLE);content.addView(list,new LinearLayout.LayoutParams(-1,0,1));
        list.setOnItemClickListener((p,v,i,id)->{if(list.isItemChecked(i))selected.add(rows.get(i).id);else selected.remove(rows.get(i).id);updateCount();});
        list.setOnItemLongClickListener((p,v,i,id)->{PopupMenu menu=new PopupMenu(host,v);menu.getMenu().add("上移").setEnabled(i>0);menu.getMenu().add("下移").setEnabled(i+1<rows.size());menu.setOnMenuItemClickListener(item->{move(i,item.getTitle().equals("上移")?-1:1);return true;});menu.show();return true;});
        error=Ui.text(host,"",12,R.color.accent);content.addView(error);
        LinearLayout footer=Ui.row(host);Ui.weighted(footer,Ui.quiet(host,"取消",this::dismiss),1);Ui.weighted(footer,Ui.primary(host,"生成 EPUB",this::generate),1);content.addView(footer);
        content.addOnLayoutChangeListener((v,left,top,right,bottom,oldLeft,oldTop,oldRight,oldBottom)->{
            int height=Math.min(Ui.dp(host,360),Math.max(Ui.dp(host,80),bottom-top-Ui.dp(host,220)));
            LinearLayout.LayoutParams params=(LinearLayout.LayoutParams)controls.getLayoutParams();if(params.height!=height){params.height=height;controls.setLayoutParams(params);}
        });
        setContentView(content,new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT));content.requestFocus();render();
    }
    @Override protected void onStart(){
        super.onStart();getWindow().setLayout(Math.min(Ui.dp(host,720),host.getResources().getDisplayMetrics().widthPixels),ViewGroup.LayoutParams.MATCH_PARENT);getWindow().setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams p=(LinearLayout.LayoutParams)controls.getLayoutParams();p.height=Ui.dp(host,Math.min(360,Math.max(96,host.getResources().getConfiguration().screenHeightDp-220)));controls.setLayoutParams(p);
    }
    private void chooseGroup(String kind,Map<String,Set<String>> groups){
        List<String> names=new ArrayList<>(groups.keySet());String[] labels=new String[names.size()];for(int i=0;i<names.size();i++)labels[i]=names.get(i)+"（"+groups.get(names.get(i)).size()+" 篇）";
        groupDialog=new AlertDialog.Builder(host).setTitle("按"+kind+"选择").setItems(labels,(d,i)->select(groups.get(names.get(i)))).setNegativeButton("取消",null).show();
    }
    void select(Set<String> ids){selected.clear();for(Article a:rows)if(ids==null||ids.contains(a.id))selected.add(a.id);render();}
    void move(int position,int delta){int target=position+delta;if(position<0||target<0||target>=rows.size())return;Collections.swap(rows,position,target);render();list.setSelection(target);}
    private void render(){
        if(list==null)return;List<String> labels=new ArrayList<>();for(Article a:rows)labels.add((a.outside?"时间线之外":PartialDate.label(a.date))+"  ·  "+a.title);
        list.setAdapter(new ArrayAdapter<>(host,android.R.layout.simple_list_item_multiple_choice,labels));
        for(int i=0;i<rows.size();i++)list.setItemChecked(i,selected.contains(rows.get(i).id));updateCount();
    }
    private void updateCount(){count.setText("已选择 "+selected.size()+" / "+rows.size()+" 篇");if(error!=null)error.setText("");}
    List<String> selectedIds(){List<String> ids=new ArrayList<>();for(Article a:rows)if(selected.contains(a.id))ids.add(a.id);return ids;}
    void generate(){if(title.getText().toString().trim().isEmpty()||selected.isEmpty()){error.setText("请填写书名，并至少选择一篇文章。");return;}host.prepareEpub(selectedIds(),title.getText().toString().trim(),author.getText().toString().trim());dismiss();}
    Bundle captureState(){Bundle b=new Bundle();b.putString("title",title.getText().toString());b.putString("author",author.getText().toString());b.putStringArrayList("selected",new ArrayList<>(selected));ArrayList<String> order=new ArrayList<>();for(Article a:rows)order.add(a.id);b.putStringArrayList("order",order);return b;}
    @Override public void dismiss(){if(groupDialog!=null)groupDialog.dismiss();super.dismiss();}
}

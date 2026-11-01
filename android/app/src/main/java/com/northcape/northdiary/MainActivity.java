package com.northcape.northdiary;

import android.app.*;
import android.content.*;
import android.content.res.Configuration;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.provider.OpenableColumns;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.util.*;
import static com.northcape.northdiary.Models.*;

public final class MainActivity extends Activity {
    private DiaryStore store;
    private DraftStore drafts;
    private LinearLayout root,workspace;
    private EditorPanel editor;
    private ListView articleList;
    private EditText search;
    private List<Article> visible=new ArrayList<>();
    private String activeId,query="",tag="",pendingImageId,exportPath;
    private int tab=0,space=0,scroll=0;
    private boolean editing,dirty,wide,byDate=true,busy;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable journal=()->writeDraft(false);
    private final Runnable autosave=()->saveEditor(false);

    @Override public void onCreate(Bundle state) {
        String theme=getSharedPreferences("appearance",0).getString("theme","system");
        if(!theme.equals("system")) {
            Configuration override=new Configuration();
            override.uiMode=theme.equals("dark")?Configuration.UI_MODE_NIGHT_YES:Configuration.UI_MODE_NIGHT_NO;
            applyOverrideConfiguration(override);
        }
        super.onCreate(state);
        try {
            store=new DiaryStore(this,DiaryStore.activeRoot(this));drafts=new DraftStore(store.root);
            if(state!=null) {
                tab=state.getInt("tab");space=state.getInt("space");activeId=state.getString("id");editing=state.getBoolean("editing");
                query=state.getString("query","");tag=state.getString("tag","");byDate=state.getBoolean("byDate",true);scroll=state.getInt("scroll");
                pendingImageId=state.getString("image");exportPath=state.getString("export");
            }
            Article recovered=drafts.read();
            if(recovered!=null) {
                try{recovered.created=store.get(recovered.id).created;}catch(IllegalArgumentException ignored){recovered.created="";}
                activeId=recovered.id;editing=true;tab=0;dirty=true;
            }
            build(recovered);
            if(recovered!=null)Toast.makeText(this,"已恢复尚未保存的编辑内容",Toast.LENGTH_LONG).show();
        } catch(Exception e) {
            new AlertDialog.Builder(this).setTitle("无法打开档案").setMessage(e.getMessage()).setPositiveButton("关闭",(d,w)->finish()).setCancelable(false).show();
        }
    }
    private void build(Article supplied) {
        editor=null;
        root=Ui.column(this);root.setBackgroundColor(getColor(R.color.paper));
        if(Build.VERSION.SDK_INT>=30)root.setOnApplyWindowInsetsListener((v,insets)->{
            android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout()|WindowInsets.Type.ime());
            v.setPadding(safe.left,safe.top,safe.right,safe.bottom);return insets;
        });
        else root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});
        setContentView(root);root.requestApplyInsets();
        TextView brand=Ui.heading(this,"NorthDiary");brand.setPadding(Ui.dp(this,20),Ui.dp(this,8),Ui.dp(this,20),0);root.addView(brand);
        TextView subtitle=Ui.text(this,"记录时间，留存记忆。",13,R.color.muted);subtitle.setPadding(Ui.dp(this,20),0,0,Ui.dp(this,8));root.addView(subtitle);
        workspace=Ui.row(this);workspace.setGravity(Gravity.TOP);root.addView(workspace,new LinearLayout.LayoutParams(-1,0,1));
        wide=getResources().getConfiguration().screenWidthDp>=840;
        if(tab==1)workspace.addView(new PeoplePanel(this,store),new LinearLayout.LayoutParams(-1,-1));
        else if(tab==2)workspace.addView(settings(),new LinearLayout.LayoutParams(-1,-1));
        else {
            if(activeId==null||wide)buildList();
            if(activeId!=null) {
                Article a=supplied!=null?supplied:store.get(activeId);editor=new EditorPanel(this,store,a,editing);
                workspace.addView(editor,new LinearLayout.LayoutParams(0,-1,1));
                editor.post(()->editor.scrollTo(0,scroll));
            } else if(wide) {
                LinearLayout welcome=Ui.column(this);Ui.pad(welcome,32);welcome.addView(Ui.heading(this,"留一页，给此刻。"));
                welcome.addView(Ui.text(this,"选择一篇回忆，或开始记录新的故事。",17,R.color.muted));workspace.addView(welcome,new LinearLayout.LayoutParams(0,-1,1));
            }
        }
        LinearLayout nav=Ui.row(this);
        String[] names={"记忆","人物","设置"};for(int i=0;i<3;i++){final int target=i;Button b=Ui.button(this,names[i],()->navigate(target));if(i==tab)b.setTextColor(getColor(R.color.accent));Ui.weighted(nav,b,1);}
        root.addView(nav);
    }
    private void buildList() {
        LinearLayout panel=Ui.column(this);Ui.pad(panel,12);
        workspace.addView(panel,new LinearLayout.LayoutParams(wide?Ui.dp(this,320):-1,-1));
        LinearLayout top=Ui.row(this);Ui.weighted(top,Ui.heading(this,"记忆"),1);top.addView(Ui.button(this,"＋ 新建",this::newArticle));panel.addView(top);
        search=Ui.input(this,"搜索标题和正文",true);search.setText(query);panel.addView(search);
        Spinner spaces=new Spinner(this);spaces.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"时间线","时间线之外","待确认","回收站"}));
        spaces.setSelection(space);panel.addView(spaces);
        LinearLayout filters=Ui.row(this);Ui.weighted(filters,Ui.button(this,tag.isEmpty()?"筛选标签":tag,this::pickTag),1);
        Ui.weighted(filters,Ui.button(this,byDate?"按事件时间":"按创建时间",()->{byDate=!byDate;refreshList();}),1);panel.addView(filters);
        articleList=new ListView(this);articleList.setDividerHeight(Ui.dp(this,6));panel.addView(articleList,new LinearLayout.LayoutParams(-1,0,1));
        TextView empty=Ui.text(this,"这里还没有回忆。\n点「新建」，留下一段文字。",16,R.color.muted);panel.addView(empty);articleList.setEmptyView(empty);
        articleList.setOnItemClickListener((p,v,i,id)->openArticle(visible.get(i).id,false));
        Ui.watch(search,()->{query=search.getText().toString();refreshList();});
        spaces.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){
            public void onNothingSelected(android.widget.AdapterView<?> p){}
            public void onItemSelected(android.widget.AdapterView<?> p,View v,int i,long id){if(space!=i){space=i;refreshList();}}
        });refreshList();
    }
    private void refreshList() {
        if(articleList==null)return;visible=store.list(query,tag,space,byDate,null);
        articleList.setAdapter(new ArrayAdapter<Article>(this,android.R.layout.simple_list_item_2,android.R.id.text1,visible){
            @Override public View getView(int i,View view,android.view.ViewGroup parent) {
                View row=super.getView(i,view,parent);Article a=getItem(i);
                TextView title=row.findViewById(android.R.id.text1),summary=row.findViewById(android.R.id.text2);
                title.setText(a.title);title.setTextColor(getColor(R.color.ink));title.setTextSize(17);title.setMaxLines(2);
                String date=space==1?"时间线之外":PartialDate.label(a.date);
                summary.setText(date+"  ·  "+a.text.replace('\n',' '));summary.setTextColor(getColor(R.color.muted));summary.setMaxLines(2);Ui.card(row);return row;
            }
        });
    }
    private void pickTag() {
        List<String> tags=store.strings("SELECT name FROM tags ORDER BY name");tags.add(0,"全部标签");
        new AlertDialog.Builder(this).setTitle("标签筛选").setItems(tags.toArray(new String[0]),(d,i)->{tag=i==0?"":tags.get(i);if(saveEditor(true))build(null);}).show();
    }
    private void navigate(int target){if(busy||!saveEditor(true))return;tab=target;activeId=null;editing=false;scroll=0;build(null);}
    private void newArticle() {
        if(busy||!saveEditor(true))return;
        Article a=new Article();a.id=UUID.randomUUID().toString();a.outside=space==1;a.draft=true;
        activeId=a.id;editing=true;dirty=true;scroll=0;build(a);writeDraft(true);
    }
    void openArticle(String id,boolean edit) {
        if(busy||!saveEditor(true))return;activeId=id;editing=edit;tab=0;scroll=0;dirty=false;build(null);
    }
    void editArticle(Article a) {
        if(a.html.contains("-qt-")||a.html.contains("<table")) {
            new AlertDialog.Builder(this).setTitle("手机基础排版")
                .setMessage("此文章包含桌面排版。修改正文时会转换为段落、加粗、斜体和链接，复杂样式可能变化。建议先在设置里导出备份。")
                .setPositiveButton("继续编辑",(d,w)->openArticle(a.id,true)).setNegativeButton("取消",null).show();
        }else openArticle(a.id,true);
    }
    void editorChanged(){dirty=true;handler.removeCallbacks(journal);handler.removeCallbacks(autosave);handler.postDelayed(journal,150);handler.postDelayed(autosave,900);}
    private boolean writeDraft(boolean show) {
        if(!editing||editor==null||!dirty)return true;
        try{drafts.write(editor.capture());return true;}catch(Exception e){editor.status("草稿保存失败，内容仍在编辑器中");if(show)Ui.error(this,e);return false;}
    }
    private boolean saveEditor(boolean show) {
        handler.removeCallbacks(journal);handler.removeCallbacks(autosave);
        if(!editing||editor==null||!dirty)return true;
        if(!writeDraft(show))return false;
        try{store.save(editor.capture());dirty=false;drafts.clear();editor.status("已保存在本机");return true;}
        catch(Exception e){editor.status("尚未写入数据库 · 编辑内容已保留在草稿");if(show)Ui.error(this,e);return false;}
    }
    void finishEditing() {
        if(!saveEditor(true))return;
        Article a=store.get(activeId);
        if(a.draft)new AlertDialog.Builder(this).setTitle("确认这篇文章？").setMessage("确认后会进入时间线或时间线之外；也可以继续保留为待确认文章。")
            .setPositiveButton("确认文章",(d,w)->{try{a.draft=false;store.save(a);editing=false;build(null);}catch(Exception e){Ui.error(this,e);}})
            .setNegativeButton("保留待确认",(d,w)->{editing=false;build(null);}).show();
        else{editing=false;build(null);}
    }
    void backFromArticle(){if(saveEditor(true)){activeId=null;editing=false;scroll=0;build(null);}}
    void trashArticle(String id) {
        if(!saveEditor(true))return;
        new AlertDialog.Builder(this).setMessage("将文章移入回收站？可以在回收站恢复。")
            .setPositiveButton("移入",(d,w)->{try{store.deleted(id,true);activeId=null;editing=false;build(null);}catch(Exception e){Ui.error(this,e);}}).setNegativeButton("取消",null).show();
    }
    void restoreArticle(String id){try{store.deleted(id,false);activeId=null;editing=false;build(null);}catch(Exception e){Ui.error(this,e);}}
    private View settings() {
        LinearLayout content=Ui.column(this);Ui.pad(content,24);content.addView(Ui.heading(this,"设置"));
        content.addView(Ui.text(this,"NorthDiary 安卓端 0.1.0-alpha\n本地记忆档案馆 · 手机与平板共用\nAGPL-3.0-or-later",16,R.color.ink));
        content.addView(Ui.button(this,"界面主题",()->new AlertDialog.Builder(this).setTitle("界面主题").setItems(new String[]{"跟随系统","浅色 · 米色与红酒","深色"},(d,i)->{
            if(!saveEditor(true))return;getSharedPreferences("appearance",0).edit().putString("theme",new String[]{"system","light","dark"}[i]).apply();recreate();}).show()));
        content.addView(Ui.button(this,"导出完整备份 .ndiary",this::exportBackup));
        content.addView(Ui.button(this,"从完整备份恢复",()->new AlertDialog.Builder(this).setTitle("恢复完整档案")
            .setMessage("恢复会切换到备份中的完整档案，不合并记录。当前档案会保留一份恢复前快照。仅支持 schema v7 的 .ndiary 完整备份。")
            .setPositiveButton("选择备份",(d,w)->chooseDocument(102,"*/*")).setNegativeButton("取消",null).show()));
        content.addView(Ui.text(this,"初版限制：完整备份解压后最多 200 MiB；单张图片最多 32 MiB。\nGitHub 文章包交换、EPUB、随机回忆和自定义人物头像尚未实现。\n手机与平板支持横竖屏及分屏，宽度足够时显示左右两栏。",14,R.color.muted));
        content.addView(Ui.button(this,"项目源码与许可证",()->ArticleText.open(this,"https://github.com/NorthCape3179/NorthDiary")));
        return Ui.scroll(this,content);
    }
    private void chooseDocument(int code,String mime){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType(mime).addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(i,code);}
    void pickImage(){if(!saveEditor(true))return;pendingImageId=activeId;chooseDocument(101,"image/*");}
    private interface Work<T>{T run()throws Exception;}
    private interface Done<T>{void accept(T result)throws Exception;}
    private <T> void work(String title,Work<T> action,Done<T> done) {
        if(busy)return;busy=true;AlertDialog progress=new AlertDialog.Builder(this).setTitle(title).setMessage("正在处理，请稍候。").setCancelable(false).create();progress.show();
        new Thread(()->{
            try{T result=action.run();runOnUiThread(()->{if(isDestroyed()){busy=false;store.close();return;}busy=false;progress.dismiss();try{done.accept(result);}catch(Exception e){Ui.error(this,e);}});}
            catch(Exception e){runOnUiThread(()->{busy=false;if(isDestroyed()){store.close();return;}progress.dismiss();Ui.error(this,e);});}
        },"northdiary-files").start();
    }
    private void exportBackup(){work("准备完整备份",()->ArchiveService.export(this,store),file->{exportPath=file.getPath();Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/octet-stream").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"NorthDiary-"+java.time.LocalDate.now()+".ndiary");startActivityForResult(i,103);});}
    @Override protected void onActivityResult(int code,int result,Intent data) {
        super.onActivityResult(code,result,data);
        if(result!=RESULT_OK||data==null||data.getData()==null){if(code==103&&exportPath!=null){new File(exportPath).delete();exportPath=null;}return;}
        Uri uri=data.getData();
        if(code==101&&pendingImageId!=null) {
            String id=pendingImageId;pendingImageId=null;
            work("保存图片",()->copyImage(uri,id),attachment->{
                if(id.equals(activeId)&&editing&&editor!=null){editor.insertAttachment(attachment);saveEditor(true);scroll=editor.getScrollY();build(null);}
                else openArticle(id,false);
            });
        } else if(code==102)work("检查并恢复备份",()->{
            InputStream in=getContentResolver().openInputStream(uri);if(in==null)throw new IOException("无法读取备份");return ArchiveService.stage(this,in);
        },stage->{
            String old=store.root.getName();
            DiaryStore prepared=new DiaryStore(this,stage);
            if(!getSharedPreferences("archive",0).edit().putString("active",stage.getName()).putString("previous",old).commit()){
                prepared.close();throw new IOException("无法切换档案，当前档案保持不变");
            }
            store.close();store=prepared;drafts=new DraftStore(stage);activeId=null;editing=false;dirty=false;tab=0;space=0;query="";tag="";build(null);
            Toast.makeText(this,"档案恢复完成，恢复前的数据已保留",Toast.LENGTH_LONG).show();
        });
        else if(code==103&&exportPath!=null) {
            File source=new File(exportPath);exportPath=null;
            work("写入备份",()->{
                try(InputStream in=new FileInputStream(source);OutputStream out=getContentResolver().openOutputStream(uri,"wt")) {
                    if(out==null)throw new IOException("无法写入所选位置");DiaryStore.copy(in,out,220L*1024*1024);
                }finally{source.delete();}return true;
            },ok->Toast.makeText(this,"备份已导出",Toast.LENGTH_LONG).show());
        }
    }
    private Attachment copyImage(Uri uri,String article) throws Exception {
        Attachment a=new Attachment();a.id=UUID.randomUUID().toString();a.name="图片";
        try(Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){if(c!=null&&c.moveToFirst())a.name=c.getString(0);}
        a.mime=getContentResolver().getType(uri);if(a.mime==null||!a.mime.startsWith("image/"))throw new IOException("请选择图片文件");
        String suffix=a.mime.equals("image/png")?".png":a.mime.equals("image/jpeg")?".jpg":a.mime.equals("image/gif")?".gif":".image";
        a.path="attachments/"+a.id+suffix;File target=ArchiveService.attachmentFile(store.root,a.path);
        try {
            try(InputStream in=getContentResolver().openInputStream(uri);OutputStream out=new FileOutputStream(target)){if(in==null)throw new IOException("无法读取图片");DiaryStore.copy(in,out,32L*1024*1024);}
            store.addAttachment(article,a);return a;
        }catch(Exception e){target.delete();throw e;}
    }
    @Override protected void onPause(){if(editor!=null&&editing)saveEditor(false);super.onPause();}
    @Override protected void onSaveInstanceState(Bundle state) {
        if(editor!=null){writeDraft(false);scroll=editor.getScrollY();}
        state.putInt("tab",tab);state.putInt("space",space);state.putString("id",activeId);state.putBoolean("editing",editing);
        state.putString("query",query);state.putString("tag",tag);state.putBoolean("byDate",byDate);state.putInt("scroll",scroll);
        state.putString("image",pendingImageId);state.putString("export",exportPath);super.onSaveInstanceState(state);
    }
    @Override public void onBackPressed(){if(busy)return;if(activeId!=null&&tab==0)backFromArticle();else if(tab!=0)navigate(0);else if(saveEditor(true))super.onBackPressed();}
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);if(store!=null&&!busy)store.close();super.onDestroy();}
}

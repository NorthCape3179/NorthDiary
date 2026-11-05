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
    private MemoryPanel memories;
    private GitHubLoginDialog githubDialog;
    private String activeId,pendingImageId,exportPath;
    String query="",tag="",category="",lastRandomId="";
    EpubExportDialog epubDialog;
    RandomMemoryDialog randomDialog;
    EpubImportService.Preview pendingEpubImport;
    AlertDialog importPreviewDialog;
    private String importSourcePath;
    int space=0;
    int timelineIndex=0,timelineOffset=0;
    boolean byDate=true;
    private int tab=0,scroll=0;
    private boolean editing,dirty,wide,busy;
    private AlertDialog fileProgress;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable journal=()->writeDraft(false);
    private final Runnable autosave=()->saveEditor(false);

    @Override protected void attachBaseContext(Context base){super.attachBaseContext(Appearance.wrap(base));}

    @Override public void onCreate(Bundle state) {
        setTheme(Appearance.choice(this).equals("forest")?R.style.ForestTheme:R.style.AppTheme);
        super.onCreate(state);
        try {
            store=new DiaryStore(this,DiaryStore.activeRoot(this));drafts=new DraftStore(store.root);
            if(state!=null) {
                tab=state.getInt("tab");space=state.getInt("space");activeId=state.getString("id");editing=state.getBoolean("editing");
                timelineIndex=state.getInt("timelineIndex");timelineOffset=state.getInt("timelineOffset");
                query=state.getString("query","");tag=state.getString("tag","");byDate=state.getBoolean("byDate",true);scroll=state.getInt("scroll");
                category=state.getString("category","");lastRandomId=state.getString("lastRandomId","");
                pendingImageId=state.getString("image");exportPath=state.getString("export");
                importSourcePath=state.getString("epubImportSource");
            }
            Article recovered=drafts.read();
            if(recovered!=null) {
                try{Article saved=store.get(recovered.id);recovered.created=saved.created;if(recovered.categories==null)recovered.categories=saved.categories;}catch(IllegalArgumentException ignored){recovered.created="";}
                activeId=recovered.id;editing=true;if(tab!=3)tab=0;dirty=true;
            }
            build(recovered);
            if(state!=null&&state.getBundle("epubSelection")!=null)showEpubExport(state.getBundle("epubSelection"));
            if(importSourcePath!=null){String path=importSourcePath;handler.post(()->work("检查 EPUB",()->EpubImportService.prepare(this,store,new File(path)),this::showImportPreview));}
            if(recovered!=null)Toast.makeText(this,"已恢复尚未保存的编辑内容",Toast.LENGTH_LONG).show();
        } catch(Exception e) {
            new AlertDialog.Builder(this).setTitle("无法打开档案").setMessage(e.getMessage()).setPositiveButton("关闭",(d,w)->finish()).setCancelable(false).show();
        }
    }
    private void build(Article supplied) {
        editor=null;memories=null;
        root=Ui.column(this);root.setBackgroundColor(Ui.color(this,R.color.paper));root.setFocusableInTouchMode(true);root.setDefaultFocusHighlightEnabled(false);
        setContentView(root);root.requestApplyInsets();
        if(Build.VERSION.SDK_INT>=26){
            boolean light=(getResources().getConfiguration().uiMode&Configuration.UI_MODE_NIGHT_MASK)!=Configuration.UI_MODE_NIGHT_YES;
            getWindow().getDecorView().setSystemUiVisibility(light?View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR:0);
        }
        LinearLayout header=Ui.row(this);header.setPadding(Ui.dp(this,22),Ui.dp(this,12),Ui.dp(this,22),Ui.dp(this,12));
        LinearLayout mark=Ui.row(this);mark.setGravity(Gravity.CENTER);mark.setBackground(Ui.surface(this,R.color.accent,13,false));mark.addView(new ArchiveIcon(this,"compass",R.color.on_accent,25));
        header.addView(mark,new LinearLayout.LayoutParams(Ui.dp(this,42),Ui.dp(this,42)));
        LinearLayout brand=Ui.column(this);brand.setPadding(Ui.dp(this,12),0,0,0);TextView name=Ui.heading(this,"NorthDiary");name.setTextSize(20);brand.addView(name);
        if(!Ui.compact(this)){Ui.gap(brand,2);TextView motto=Ui.text(this,"你的私人记忆档案馆",11,R.color.muted);brand.addView(motto);}
        header.addView(brand,new LinearLayout.LayoutParams(0,-2,1));
        TextView badge=Ui.text(this,"本地 · 离线",10,R.color.accent);badge.setBackground(Ui.surface(this,R.color.soft,10,false));badge.setPadding(Ui.dp(this,9),Ui.dp(this,6),Ui.dp(this,9),Ui.dp(this,6));header.addView(badge);root.addView(header);
        workspace=Ui.row(this);workspace.setGravity(Gravity.TOP);root.addView(workspace,new LinearLayout.LayoutParams(-1,0,1));
        wide=getResources().getConfiguration().screenWidthDp>=840;
        if(tab==1)workspace.addView(new PeoplePanel(this,store),new LinearLayout.LayoutParams(-1,-1));
        else if(tab==2)workspace.addView(settings(),new LinearLayout.LayoutParams(-1,-1));
        else {
            if(activeId==null||wide){
                if(tab==3)workspace.addView(new TimelinePanel(this,store,activeId),new LinearLayout.LayoutParams(wide?Ui.dp(this,380):-1,-1));
                else buildList();
            }
            if(activeId!=null) {
                Article a=supplied!=null?supplied:store.get(activeId);editor=new EditorPanel(this,store,a,editing);
                LinearLayout.LayoutParams pane=new LinearLayout.LayoutParams(0,-1,1);pane.setMargins(Ui.dp(this,wide?8:12),0,Ui.dp(this,wide?20:12),0);editor.setBackground(Ui.surface(this,R.color.card,24,true));workspace.addView(editor,pane);
                EditorPanel shown=editor;int position=scroll;
                shown.post(()->{if(editor==shown&&!isDestroyed())shown.scrollTo(0,position);});
            } else if(wide) {
                View welcome=Ui.empty(this,"留一页，给此刻。","选择一篇回忆，或开始记录新的故事。","写一篇回忆",this::newArticle);
                welcome.setBackground(Ui.surface(this,R.color.card,24,true));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,-1,1);p.setMargins(Ui.dp(this,8),0,Ui.dp(this,20),0);workspace.addView(welcome,p);
            }
        }
        FrameLayout footer=new FrameLayout(this);footer.setPadding(Ui.dp(this,16),Ui.dp(this,10),Ui.dp(this,16),Ui.dp(this,10));
        FrameLayout.LayoutParams nav=new FrameLayout.LayoutParams(Math.min(Ui.dp(this,540),Ui.dp(this,getResources().getConfiguration().screenWidthDp-32)),-2,Gravity.CENTER);
        footer.addView(Ui.navigation(this,tab,this::navigate),nav);root.addView(footer);KeyboardInsets.bind(this,root,footer);root.requestFocus();
    }
    private void buildList() {
        memories=new MemoryPanel(this,store);workspace.addView(memories,new LinearLayout.LayoutParams(wide?Ui.dp(this,360):-1,-1));
    }
    private void refreshList() {
        if(memories!=null)memories.refresh();
    }
    void pickTag() {
        if(!saveEditor(true))return;
        List<String> tags=store.strings("SELECT name FROM tags ORDER BY name");tags.add(0,"全部标签");
        new AlertDialog.Builder(this).setTitle("标签筛选").setItems(tags.toArray(new String[0]),(d,i)->{tag=i==0?"":tags.get(i);build(null);}).show();
    }
    void pickCategory() {
        if(!saveEditor(true))return;
        List<String> names=store.strings("SELECT name FROM categories ORDER BY name");names.add(0,"全部分类");
        new AlertDialog.Builder(this).setTitle("分类筛选").setItems(names.toArray(new String[0]),(d,i)->{category=i==0?"":names.get(i);build(null);}).show();
    }
    void randomMemory(){
        if(busy||!saveEditor(true))return;
        randomDialog=new RandomMemoryDialog(this,store);randomDialog.show();
    }
    void exportEpub(){if(!busy&&saveEditor(true))showEpubExport(null);}
    void importEpub(){if(!busy&&saveEditor(true))chooseDocument(105,"application/epub+zip");}
    void showImportPreview(EpubImportService.Preview preview){
        pendingEpubImport=preview;importSourcePath=preview.source.getPath();
        LinearLayout content=Ui.column(this);Ui.pad(content,20);content.addView(Ui.text(this,preview.summary(),14,R.color.accent));Ui.gap(content,12);
        content.addView(Ui.text(this,"重复副本会跳过；内容冲突会另存副本，保留本地文章和人物。正文转换为手机基础排版，图片显示为文件名链接。",13,R.color.muted));Ui.gap(content,12);
        for(int i=0;i<Math.min(preview.entries.size(),8);i++)content.addView(Ui.text(this,"· "+preview.entries.get(i).record.optString("title"),14,R.color.ink));
        if(preview.entries.size()>8)content.addView(Ui.text(this,"以及其余 "+(preview.entries.size()-8)+" 篇",12,R.color.muted));
        ScrollView scroll=new ScrollView(this);scroll.addView(content);
        importPreviewDialog=new AlertDialog.Builder(this).setTitle("导入预览").setView(scroll).setPositiveButton("确认导入",(d,w)->applyEpubImport()).setNegativeButton("取消",(d,w)->cancelEpubImport()).create();
        importPreviewDialog.setOnCancelListener(d->cancelEpubImport());importPreviewDialog.show();
    }
    private void cancelEpubImport(){if(pendingEpubImport!=null)pendingEpubImport.close(false);pendingEpubImport=null;importSourcePath=null;}
    void applyEpubImport(){
        EpubImportService.Preview preview=pendingEpubImport;if(preview==null)return;pendingEpubImport=null;importSourcePath=null;
        work("导入文集",()->{try{return EpubImportService.apply(store,preview);}finally{preview.close(false);}},result->{activeId=null;editing=false;dirty=false;tab=0;space=0;query="";tag="";category="";build(null);Toast.makeText(this,"已导入 "+result.imported+" 篇，跳过 "+result.skipped+" 篇，冲突副本 "+result.conflicts+" 篇",Toast.LENGTH_LONG).show();});
    }
    private void showEpubExport(Bundle state){epubDialog=new EpubExportDialog(this,store,state);epubDialog.show();}
    private void navigate(int target){if(busy||!saveEditor(true))return;tab=target;activeId=null;editing=false;scroll=0;build(null);}
    void newArticle() {
        if(busy||!saveEditor(true))return;
        Article a=new Article();a.id=UUID.randomUUID().toString();a.outside=tab==0&&space==1;a.draft=true;
        activeId=a.id;editing=true;dirty=true;scroll=0;build(a);writeDraft(true);
    }
    void openArticle(String id,boolean edit) {
        if(busy||!saveEditor(true))return;activeId=id;editing=edit;if(tab!=3)tab=0;scroll=0;dirty=false;build(null);
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
    private View settings() {return new SettingsPanel(this,store);}
    void githubLogin(){githubDialog=new GitHubLoginDialog(this);}
    void refreshAccount(){if(tab==2&&!isDestroyed())build(null);}
    AlertDialog themeDialog;
    void showThemePicker(){
        String[] values={"system","light","dark","forest"};String selected=Appearance.choice(this);int index=0;
        for(int i=0;i<values.length;i++)if(values[i].equals(selected))index=i;
        themeDialog=new AlertDialog.Builder(this).setTitle("界面主题")
            .setSingleChoiceItems(new String[]{"跟随系统","浅色 · 米色与红酒","深色 · 暮色酒红","深色 · 森林绿"},index,(dialog,i)->{dialog.dismiss();setThemeChoice(values[i]);})
            .setNegativeButton("取消",null).show();
    }
    void setThemeChoice(String choice){
        if(busy||!saveEditor(true))return;
        if(!Arrays.asList("system","light","dark","forest").contains(choice))throw new IllegalArgumentException("未知主题");
        if(!getSharedPreferences("appearance",0).edit().putString("theme",choice).commit()){
            Ui.error(this,new IOException("主题设置保存失败，请重试"));return;
        }
        recreate();
    }
    void requestRestore(){new AlertDialog.Builder(this).setTitle("恢复完整档案")
        .setMessage("恢复会切换到备份中的完整档案，不合并记录。当前档案会保留，可在设置中切回。仅支持 schema v7 的 .ndiary 完整备份。")
        .setPositiveButton("选择备份",(d,w)->chooseDocument(102,"*/*")).setNegativeButton("取消",null).show();}
    void previousArchive(String previous){new AlertDialog.Builder(this).setMessage("切换到上一次恢复前的档案？当前档案也会保留。")
        .setPositiveButton("切换",(d,w)->work("检查档案",()->{File old=new File(getFilesDir(),previous);ArchiveService.validate(old);return old;},this::activateRoot))
        .setNegativeButton("取消",null).show();}
    private void chooseDocument(int code,String mime){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType(mime).addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(i,code);}
    void pickImage(){if(!saveEditor(true))return;pendingImageId=activeId;chooseDocument(101,"image/*");}
    private interface Work<T>{T run()throws Exception;}
    private interface Done<T>{void accept(T result)throws Exception;}
    private <T> void work(String title,Work<T> action,Done<T> done) {
        if(busy)return;busy=true;AlertDialog progress=new AlertDialog.Builder(this).setTitle(title).setMessage("正在处理，请稍候。").setCancelable(false).create();fileProgress=progress;progress.show();
        new Thread(()->{
            try{T result=action.run();runOnUiThread(()->{progress.dismiss();if(isDestroyed()){busy=false;if(result instanceof EpubImportService.Preview)((EpubImportService.Preview)result).close(false);store.close();return;}busy=false;try{done.accept(result);}catch(Exception e){Ui.error(this,e);}});}
            catch(Exception e){runOnUiThread(()->{busy=false;progress.dismiss();if(isDestroyed()){store.close();return;}Ui.error(this,e);});}
        },"northdiary-files").start();
    }
    void exportBackup(){work("准备完整备份",()->ArchiveService.export(this,store),file->{exportPath=file.getPath();Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/octet-stream").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"NorthDiary-"+java.time.LocalDate.now()+".ndiary");startActivityForResult(i,103);});}
    void prepareEpub(List<String> ids,String title,String author){
        work("生成 EPUB 文集",()->EpubService.export(this,store,ids,title,author),file->{exportPath=file.getPath();chooseEpubDestination();});
    }
    private void chooseEpubDestination(){
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/epub+zip").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"NorthDiary-"+java.time.LocalDate.now()+".epub");startActivityForResult(intent,104);
    }
    @Override protected void onActivityResult(int code,int result,Intent data) {
        super.onActivityResult(code,result,data);
        if(result!=RESULT_OK||data==null||data.getData()==null){if((code==103||code==104)&&exportPath!=null){new File(exportPath).delete();exportPath=null;}return;}
        Uri uri=data.getData();
        if(code==101&&pendingImageId!=null) {
            String id=pendingImageId;pendingImageId=null;
            work("保存图片",()->copyImage(uri,id),attachment->{
                if(id.equals(activeId)&&editing&&editor!=null){editor.insertAttachment(attachment);saveEditor(true);scroll=editor.getScrollY();build(null);}
                else openArticle(id,false);
            });
        } else if(code==102)work("检查并恢复备份",()->{
            InputStream in=getContentResolver().openInputStream(uri);if(in==null)throw new IOException("无法读取备份");return ArchiveService.stage(this,in);
        },this::activateRoot);
        else if(code==105)work("检查 EPUB",()->{
            InputStream in=getContentResolver().openInputStream(uri);if(in==null)throw new IOException("无法读取 EPUB");return EpubImportService.prepare(this,store,in);
        },this::showImportPreview);
        else if((code==103||code==104)&&exportPath!=null) {
            File source=new File(exportPath);exportPath=null;
            work(code==104?"保存 EPUB 文集":"写入备份",()->{
                try(InputStream in=new FileInputStream(source);OutputStream out=getContentResolver().openOutputStream(uri,"wt")) {
                    if(out==null)throw new IOException("无法写入所选位置");DiaryStore.copy(in,out,220L*1024*1024);
                }finally{source.delete();}return true;
            },ok->Toast.makeText(this,code==104?"EPUB 文集已导出":"备份已导出",Toast.LENGTH_LONG).show());
        }
    }
    private void activateRoot(File stage)throws Exception {
        String old=store.root.getName();DiaryStore prepared=new DiaryStore(this,stage);
        if(!getSharedPreferences("archive",0).edit().putString("active",stage.getName()).putString("previous",old).commit()){
            prepared.close();throw new IOException("无法切换档案，当前档案保持不变");
        }
        store.close();store=prepared;drafts=new DraftStore(stage);activeId=null;editing=false;dirty=false;tab=0;space=0;query="";tag="";category="";build(null);
        Toast.makeText(this,"档案切换完成，切换前的数据已保留",Toast.LENGTH_LONG).show();
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
        state.putInt("timelineIndex",timelineIndex);state.putInt("timelineOffset",timelineOffset);
        state.putString("query",query);state.putString("tag",tag);state.putBoolean("byDate",byDate);state.putInt("scroll",scroll);
        state.putString("category",category);state.putString("lastRandomId",lastRandomId);
        if(epubDialog!=null&&epubDialog.isShowing())state.putBundle("epubSelection",epubDialog.captureState());
        if(pendingEpubImport!=null)state.putString("epubImportSource",importSourcePath);
        state.putString("image",pendingImageId);state.putString("export",exportPath);super.onSaveInstanceState(state);
    }
    @Override public void onBackPressed(){if(busy)return;if(activeId!=null&&(tab==0||tab==3))backFromArticle();else if(tab!=0)navigate(0);else if(saveEditor(true))super.onBackPressed();}
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);if(githubDialog!=null)githubDialog.dismiss();if(epubDialog!=null)epubDialog.dismiss();if(randomDialog!=null)randomDialog.dismiss();if(importPreviewDialog!=null)importPreviewDialog.dismiss();if(fileProgress!=null)fileProgress.dismiss();if(pendingEpubImport!=null)pendingEpubImport.close(isChangingConfigurations());if(store!=null&&!busy)store.close();super.onDestroy();}
}

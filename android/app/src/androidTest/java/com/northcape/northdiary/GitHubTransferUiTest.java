package com.northcape.northdiary;

import android.app.*;
import android.content.Context;
import android.os.Bundle;
import android.test.ActivityInstrumentationTestCase2;
import android.view.*;
import android.widget.*;
import java.io.File;
import java.util.UUID;
import static com.northcape.northdiary.Models.*;

public class GitHubTransferUiTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public GitHubTransferUiTest(){super(MainActivity.class);}
    private MainActivity current;private File root;private String oldRoot,oldTheme,oldRepository,oldDraft;
    @Override protected void setUp()throws Exception{
        super.setUp();Context c=getInstrumentation().getTargetContext();oldRoot=c.getSharedPreferences("archive",0).getString("active","store-initial");oldTheme=Appearance.choice(c);oldRepository=c.getSharedPreferences("github-config",0).getString("repository","");oldDraft=c.getSharedPreferences("github-config",0).getString("repository-draft","");String name="github-ui-"+UUID.randomUUID();root=new File(c.getFilesDir(),name);
        c.getSharedPreferences("archive",0).edit().putString("active",name).commit();c.getSharedPreferences("appearance",0).edit().putString("theme","forest").commit();c.getSharedPreferences("github-config",0).edit().remove("repository").remove("repository-draft").commit();
        try(DiaryStore store=new DiaryStore(c,root)){Article a=new Article();a.id=UUID.randomUUID().toString();a.title="留在湖边的一封信";a.date="2026-11-05";a.html="<p>在普通日子里，保存一段想重访的记忆。</p>";a.text="在普通日子里，保存一段想重访的记忆。";store.save(a);}
    }
    private View find(View root,String text){if(root instanceof TextView&&text.contentEquals(((TextView)root).getText()))return root;if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){View found=find(((ViewGroup)root).getChildAt(i),text);if(found!=null)return found;}return null;}
    private void click(String label)throws Throwable{runTestOnUiThread(()->{View view=find(current.getWindow().getDecorView(),label);assertNotNull(label,view);while(!view.hasOnClickListeners()&&view.getParent() instanceof View)view=(View)view.getParent();assertTrue(view.performClick());});getInstrumentation().waitForIdleSync();}
    public void testVisibleSettingsEntriesInitializationCancellationAndExportDestinationRecreation()throws Throwable{
        current=getActivity();getInstrumentation().waitForIdleSync();UiTestCapture.save(getInstrumentation(),"14-home-green-gray");click("设置");
        runTestOnUiThread(()->{assertNotNull(find(current.getWindow().getDecorView(),"导出到 GitHub"));assertNotNull(find(current.getWindow().getDecorView(),"从 GitHub 导入"));assertNotNull(find(current.getWindow().getDecorView(),"私有数据仓库"));});
        UiTestCapture.save(getInstrumentation(),"15-settings-github");click("导出到 GitHub");
        runTestOnUiThread(()->{assertTrue(current.githubTransferDialog.dialog.isShowing());View decor=current.githubTransferDialog.dialog.getWindow().getDecorView();((EditText)decor.findViewWithTag("github-repository")).setText("qa/NorthDiary-Data");find(decor,"初始化空仓库").performClick();assertTrue(current.githubTransferDialog.initializationDialog.isShowing());});
        runTestOnUiThread(()->current.githubTransferDialog.initializationDialog.getButton(AlertDialog.BUTTON_NEGATIVE).performClick());getInstrumentation().waitForIdleSync();assertEquals("",current.getSharedPreferences("github-config",0).getString("repository",""));
        runTestOnUiThread(()->{
            current.githubTransferDialog.dismiss();Bundle state=new Bundle();state.putString("githubRepository","qa/NorthDiary-Data");current.epubDialog=new EpubExportDialog(current,current.diaryStore(),state);current.epubDialog.show();assertNotNull(find(current.epubDialog.getWindow().getDecorView(),"上传文集"));
        });
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);getInstrumentation().addMonitor(monitor);runTestOnUiThread(current::recreate);current=(MainActivity)monitor.waitForActivityWithTimeout(10000);getInstrumentation().removeMonitor(monitor);assertNotNull(current);getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{assertEquals("qa/NorthDiary-Data",current.epubDialog.captureState().getString("githubRepository"));View button=find(current.epubDialog.getWindow().getDecorView(),"上传文集");assertNotNull(button);assertTrue(button.getGlobalVisibleRect(new android.graphics.Rect()));});UiTestCapture.save(getInstrumentation(),"16-github-export-selection");runTestOnUiThread(()->current.epubDialog.dismiss());
    }
    @Override protected void tearDown()throws Exception{if(current!=null){getInstrumentation().runOnMainSync(()->current.finish());getInstrumentation().waitForIdleSync();}Context c=getInstrumentation().getTargetContext();c.getSharedPreferences("archive",0).edit().putString("active",oldRoot).commit();c.getSharedPreferences("appearance",0).edit().putString("theme",oldTheme).commit();c.getSharedPreferences("github-config",0).edit().putString("repository",oldRepository).putString("repository-draft",oldDraft).commit();if(root!=null)ArchiveService.remove(root);super.tearDown();}
}

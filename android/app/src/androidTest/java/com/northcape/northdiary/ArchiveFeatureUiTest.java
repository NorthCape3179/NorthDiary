package com.northcape.northdiary;

import android.app.*;
import android.content.Context;
import android.test.ActivityInstrumentationTestCase2;
import android.view.*;
import android.widget.*;
import java.io.File;
import java.util.*;
import static com.northcape.northdiary.Models.*;

public class ArchiveFeatureUiTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public ArchiveFeatureUiTest(){super(MainActivity.class);}
    private MainActivity current;private File root;private String oldRoot,oldTheme,first,second;
    @Override protected void setUp()throws Exception{
        super.setUp();Context c=getInstrumentation().getTargetContext();oldRoot=c.getSharedPreferences("archive",0).getString("active","store-initial");oldTheme=Appearance.choice(c);
        String name="archive-ui-"+UUID.randomUUID();root=new File(c.getFilesDir(),name);c.getSharedPreferences("archive",0).edit().putString("active",name).commit();c.getSharedPreferences("appearance",0).edit().putString("theme","light").commit();
        try(DiaryStore store=new DiaryStore(c,root)){
            first=add(store,"校园里的一段往事","校园",false);second=add(store,"不需要日期的信","旅行",true);
            store.getWritableDatabase().execSQL("INSERT INTO article_temporary_tags VALUES (?, '临时回忆')",new Object[]{first});
        }
    }
    private String add(DiaryStore store,String title,String category,boolean outside){Article a=new Article();a.id=UUID.randomUUID().toString();a.title=title;a.date="2026";a.outside=outside;a.categories=Collections.singletonList(category);a.tags.add("回忆");a.html="<p>湖边的风吹过校园，我们把平常的一天留在这里。</p>";a.text="湖边的风吹过校园，我们把平常的一天留在这里。";store.save(a);return a.id;}
    private View text(View root,String label){if(root instanceof TextView&&label.contentEquals(((TextView)root).getText()))return root;if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){View found=text(((ViewGroup)root).getChildAt(i),label);if(found!=null)return found;}return null;}
    public void testRandomPreviewAndExportGroupSelectionRecreation()throws Throwable{
        current=getActivity();getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{View button=text(current.getWindow().getDecorView(),"随机回忆");assertNotNull(button);button.performClick();});getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{assertTrue(current.randomDialog.isShowing());String previous=current.lastRandomId;current.randomDialog.getButton(AlertDialog.BUTTON_NEUTRAL).performClick();assertFalse(previous.equals(current.lastRandomId));});
        UiTestCapture.save(getInstrumentation(),"09-random-memory");
        runTestOnUiThread(()->{current.randomDialog.dismiss();text(current.getWindow().getDecorView(),"导出文集").performClick();});getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{
            EpubExportDialog dialog=current.epubDialog;assertEquals(2,dialog.selectedIds().size());View decor=dialog.getWindow().getDecorView();text(decor,"取消全选").performClick();assertEquals(0,dialog.selectedIds().size());dialog.generate();assertTrue(dialog.isShowing());
            text(decor,"按标签选择").performClick();ListView groups=dialog.groupDialog.getListView();int position=-1;for(int i=0;i<groups.getCount();i++)if(groups.getItemAtPosition(i).toString().startsWith("临时回忆"))position=i;assertTrue(position>=0);groups.performItemClick(null,position,position);assertEquals(Collections.singletonList(first),dialog.selectedIds());
            text(decor,"全选").performClick();assertEquals(2,dialog.selectedIds().size());text(decor,"按分类选择").performClick();groups=dialog.groupDialog.getListView();position=-1;for(int i=0;i<groups.getCount();i++)if(groups.getItemAtPosition(i).toString().startsWith("校园"))position=i;assertTrue(position>=0);groups.performItemClick(null,position,position);assertEquals(Collections.singletonList(first),dialog.selectedIds());
            ((EditText)decor.findViewWithTag("epub-title")).setText("我的回忆文集");dialog.move(1,-1);
        });
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);getInstrumentation().addMonitor(monitor);runTestOnUiThread(current::recreate);
        current=(MainActivity)monitor.waitForActivityWithTimeout(10000);getInstrumentation().removeMonitor(monitor);assertNotNull(current);getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{assertTrue(current.epubDialog.isShowing());assertEquals(Collections.singletonList(first),current.epubDialog.selectedIds());assertEquals("我的回忆文集",((EditText)current.epubDialog.getWindow().getDecorView().findViewWithTag("epub-title")).getText().toString());});
        UiTestCapture.save(getInstrumentation(),"10-export-selection");runTestOnUiThread(()->current.epubDialog.dismiss());
    }
    @Override protected void tearDown()throws Exception{
        if(current!=null){getInstrumentation().runOnMainSync(()->current.finish());getInstrumentation().waitForIdleSync();}
        Context c=getInstrumentation().getTargetContext();c.getSharedPreferences("archive",0).edit().putString("active",oldRoot).commit();c.getSharedPreferences("appearance",0).edit().putString("theme",oldTheme).commit();if(root!=null)ArchiveService.remove(root);super.tearDown();
    }
}

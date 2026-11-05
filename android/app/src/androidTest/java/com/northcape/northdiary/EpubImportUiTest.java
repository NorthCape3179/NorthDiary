package com.northcape.northdiary;

import android.app.*;
import android.content.Context;
import android.test.ActivityInstrumentationTestCase2;
import android.util.Base64;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.util.UUID;

public class EpubImportUiTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public EpubImportUiTest(){super(MainActivity.class);}
    private MainActivity current;private File root;private String oldRoot;
    @Override protected void setUp()throws Exception{super.setUp();Context context=getInstrumentation().getTargetContext();oldRoot=context.getSharedPreferences("archive",0).getString("active","store-initial");String name="epub-ui-"+UUID.randomUUID();root=new File(context.getFilesDir(),name);context.getSharedPreferences("archive",0).edit().putString("active",name).commit();}
    private EpubImportService.Preview prepare()throws Exception{try(InputStream in=getInstrumentation().getContext().getAssets().open("desktop-v4.epub.base64");DiaryStore store=new DiaryStore(getInstrumentation().getTargetContext(),root)){byte[] data=Base64.decode(DiaryStore.readBytes(in,128*1024),Base64.DEFAULT);return EpubImportService.prepare(getInstrumentation().getTargetContext(),store,new ByteArrayInputStream(data));}}
    private int count(){try(DiaryStore store=new DiaryStore(getInstrumentation().getTargetContext(),root)){return store.exportable().size();}}
    private View text(View view,String value){if(view instanceof TextView&&value.contentEquals(((TextView)view).getText()))return view;if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){View found=text(((ViewGroup)view).getChildAt(i),value);if(found!=null)return found;}return null;}
    public void testPreviewCancelRotationAndConfirmedImport()throws Throwable{
        current=getActivity();getInstrumentation().waitForIdleSync();EpubImportService.Preview first=prepare();File source=first.source;
        runTestOnUiThread(()->{current.showImportPreview(first);assertTrue(current.importPreviewDialog.isShowing());});assertEquals(0,count());
        runTestOnUiThread(()->current.importPreviewDialog.getButton(AlertDialog.BUTTON_NEGATIVE).performClick());assertFalse(source.exists());assertEquals(0,count());
        EpubImportService.Preview second=prepare();runTestOnUiThread(()->current.showImportPreview(second));
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);getInstrumentation().addMonitor(monitor);runTestOnUiThread(current::recreate);current=(MainActivity)monitor.waitForActivityWithTimeout(10000);getInstrumentation().removeMonitor(monitor);assertNotNull(current);
        long until=android.os.SystemClock.uptimeMillis()+10000;boolean[] ready={false};
        do{getInstrumentation().runOnMainSync(()->ready[0]=current.pendingEpubImport!=null&&current.importPreviewDialog!=null&&current.importPreviewDialog.isShowing());if(ready[0])break;Thread.sleep(100);}while(android.os.SystemClock.uptimeMillis()<until);
        assertTrue("Import preview must survive rotation",ready[0]);assertEquals(0,count());UiTestCapture.save(getInstrumentation(),"12-import-preview");
        runTestOnUiThread(()->current.importPreviewDialog.getButton(AlertDialog.BUTTON_POSITIVE).performClick());until=android.os.SystemClock.uptimeMillis()+10000;while(count()!=2&&android.os.SystemClock.uptimeMillis()<until)Thread.sleep(100);assertEquals(2,count());getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->assertNotNull(text(current.getWindow().getDecorView(),"记忆档案")));UiTestCapture.save(getInstrumentation(),"13-import-complete");
    }
    @Override protected void tearDown()throws Exception{if(current!=null){getInstrumentation().runOnMainSync(()->current.finish());getInstrumentation().waitForIdleSync();}getInstrumentation().getTargetContext().getSharedPreferences("archive",0).edit().putString("active",oldRoot).commit();if(root!=null)ArchiveService.remove(root);super.tearDown();}
}

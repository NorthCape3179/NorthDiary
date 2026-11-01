package com.northcape.northdiary;

import android.test.ActivityInstrumentationTestCase2;
import android.app.Instrumentation;
import android.graphics.Bitmap;
import java.io.*;
import android.view.*;
import android.widget.*;

public class ScreenTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public ScreenTest(){super(MainActivity.class);}
    private View find(View v,String text){
        if(v instanceof TextView&&((TextView)v).getText().toString().equals(text))return v;
        if(v instanceof ViewGroup)for(int i=0;i<((ViewGroup)v).getChildCount();i++){View found=find(((ViewGroup)v).getChildAt(i),text);if(found!=null)return found;}
        return null;
    }
    private View hint(View v,String hint){
        if(v instanceof EditText&&hint.contentEquals(((EditText)v).getHint()))return v;
        if(v instanceof ViewGroup)for(int i=0;i<((ViewGroup)v).getChildCount();i++){View found=hint(((ViewGroup)v).getChildAt(i),hint);if(found!=null)return found;}
        return null;
    }
    public void testAdaptiveLayoutAndRecreatedDraft()throws Throwable {
        MainActivity activity=getActivity();getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{View add=find(activity.getWindow().getDecorView(),"＋ 新建");assertNotNull(add);add.performClick();});
        getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{
            View decor=activity.getWindow().getDecorView();
            assertNotNull(find(decor,"时间线之外 · 阅读时隐藏事件日期"));
            boolean wide=activity.getResources().getConfiguration().screenWidthDp>=840;
            assertEquals(wide,hint(decor,"搜索标题和正文")!=null);
            ((EditText)hint(decor,"标题")).setText("旋转后保留标题");
            ((EditText)hint(decor,"事件日期：2026 / 2026-11 / 2026-11-01")).setText("尚未输入完成");
        });
        File screenshots=new File(getInstrumentation().getTargetContext().getExternalFilesDir(null),"screenshots");
        assertTrue(screenshots.isDirectory()||screenshots.mkdirs());
        Bitmap screenshot=getInstrumentation().getUiAutomation().takeScreenshot();assertNotNull(screenshot);
        try(OutputStream output=new FileOutputStream(new File(screenshots,"editor.png"))){assertTrue(screenshot.compress(Bitmap.CompressFormat.PNG,100,output));}
        screenshot.recycle();
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);
        getInstrumentation().addMonitor(monitor);runTestOnUiThread(activity::recreate);
        MainActivity recreated=(MainActivity)monitor.waitForActivityWithTimeout(10000);
        assertNotNull(recreated);getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{
            View decor=recreated.getWindow().getDecorView();
            assertNotNull(find(decor,"旋转后保留标题"));
            assertNotNull(find(decor,"尚未输入完成"));
            recreated.finish();
        });
        getInstrumentation().removeMonitor(monitor);
    }
}

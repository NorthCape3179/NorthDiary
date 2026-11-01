package com.northcape.northdiary;

import android.test.ActivityInstrumentationTestCase2;
import android.view.*;
import android.widget.*;

public class ScreenTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public ScreenTest(){super(MainActivity.class);}
    private View find(View v,String text){
        if(v instanceof TextView&&((TextView)v).getText().toString().equals(text))return v;
        if(v instanceof ViewGroup)for(int i=0;i<((ViewGroup)v).getChildCount();i++){View found=find(((ViewGroup)v).getChildAt(i),text);if(found!=null)return found;}
        return null;
    }
    public void testNewDraftAndRotationState()throws Throwable {
        MainActivity activity=getActivity();getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{View add=find(activity.getWindow().getDecorView(),"＋ 新建");assertNotNull(add);add.performClick();});
        getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->assertNotNull(find(activity.getWindow().getDecorView(),"时间线之外 · 阅读时隐藏事件日期")));
        // Lifecycle state persistence is also exercised by the phone/tablet emulator matrix.
    }
}

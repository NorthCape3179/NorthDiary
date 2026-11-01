package com.northcape.northdiary;

import android.app.Instrumentation;
import android.content.*;
import android.test.ActivityInstrumentationTestCase2;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import java.io.File;
import java.util.UUID;
import static com.northcape.northdiary.Models.*;

public class TimelineFeatureTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public TimelineFeatureTest(){super(MainActivity.class);}
    private MainActivity current;private File root;private String oldRoot,oldTheme,recentId;
    @Override protected void setUp()throws Exception {
        super.setUp();Context c=getInstrumentation().getTargetContext();oldRoot=c.getSharedPreferences("archive",0).getString("active","store-initial");oldTheme=Appearance.choice(c);
        String name="timeline-test-"+UUID.randomUUID();root=new File(c.getFilesDir(),name);c.getSharedPreferences("archive",0).edit().putString("active",name).commit();c.getSharedPreferences("appearance",0).edit().putString("theme","light").commit();
        try(DiaryStore store=new DiaryStore(c,root)){
            recentId=add(store,"最近的一天","2026-11-03",false,false,false);
            add(store,"只记得这个月","2026-11",false,false,false);add(store,"那一年的故事","2025",false,false,false);add(store,"更早的回忆","2024-02-29",false,false,false);
            add(store,"不属于时间线","2027",true,false,false);add(store,"尚未确认","2028",false,true,false);add(store,"回收站记录","2029",false,false,true);
        }
    }
    private String add(DiaryStore store,String title,String date,boolean outside,boolean draft,boolean deleted){
        Article a=new Article();a.id=UUID.randomUUID().toString();a.title=title;a.date=date;a.outside=outside;a.draft=draft;a.text="一些想保存下来的片段，沿着时间慢慢重访。";a.html="<p>"+a.text+"</p>";store.save(a);if(deleted)store.deleted(a.id,true);return a.id;
    }
    private <T extends View>T type(View view,Class<T> type){if(type.isInstance(view))return type.cast(view);if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){T match=type(((ViewGroup)view).getChildAt(i),type);if(match!=null)return match;}return null;}
    private View tag(View view,String tag){if(tag.equals(view.getTag())||tag.contentEquals(view.getContentDescription()==null?"":view.getContentDescription()))return view;if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){View match=tag(((ViewGroup)view).getChildAt(i),tag);if(match!=null)return match;}return null;}
    private EditText body(View view){if(view instanceof EditText&&"写下想留下的记忆……".contentEquals(((EditText)view).getHint()))return (EditText)view;if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){EditText match=body(((ViewGroup)view).getChildAt(i));if(match!=null)return match;}return null;}
    private void waitNavigation(boolean visible)throws Exception {
        long end=android.os.SystemClock.uptimeMillis()+8000;boolean[] state={false};
        do{getInstrumentation().runOnMainSync(()->{View nav=tag(current.getWindow().getDecorView(),"bottom-navigation");state[0]=nav!=null&&nav.getVisibility()==(visible?View.VISIBLE:View.GONE);});if(state[0])return;Thread.sleep(100);}while(android.os.SystemClock.uptimeMillis()<end);
        fail(visible?"Navigation did not return after keyboard hide":"Navigation stayed above keyboard");
    }
    public void testTimelineNavigationPartialDatesReadingRecreationAndKeyboard()throws Throwable {
        current=getActivity();getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->assertTrue(tag(current.getWindow().getDecorView(),"时间线").performClick()));getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{
            TimelinePanel panel=type(current.getWindow().getDecorView(),TimelinePanel.class);assertNotNull(panel);ListView list=type(panel,ListView.class);int count=0;
            for(int i=0;i<list.getAdapter().getCount();i++){TimelineEntries.Entry e=(TimelineEntries.Entry)list.getAdapter().getItem(i);if(e.article!=null){count++;assertFalse(e.article.title.equals("不属于时间线"));assertFalse(e.article.title.equals("尚未确认"));assertFalse(e.article.title.equals("回收站记录"));}}
            assertEquals(4,count);assertTrue(tag(current.getWindow().getDecorView(),"时间线").isSelected());
        });
        UiTestCapture.save(getInstrumentation(),"07-timeline-light");
        runTestOnUiThread(()->{ListView list=type(type(current.getWindow().getDecorView(),TimelinePanel.class),ListView.class);list.performItemClick(list.getChildAt(2),2,2);});getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{assertNotNull(tag(current.getWindow().getDecorView(),"article-reader"));assertEquals(current.getResources().getConfiguration().screenWidthDp>=840,type(current.getWindow().getDecorView(),TimelinePanel.class)!=null);current.onBackPressed();});getInstrumentation().waitForIdleSync();
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);getInstrumentation().addMonitor(monitor);runTestOnUiThread(current::recreate);
        current=(MainActivity)monitor.waitForActivityWithTimeout(10000);getInstrumentation().removeMonitor(monitor);assertNotNull(current);getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{assertNotNull(type(current.getWindow().getDecorView(),TimelinePanel.class));current.openArticle(recentId,true);});getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{EditText input=body(current.getWindow().getDecorView());assertNotNull(input);assertTrue(input.requestFocus());input.setSelection(0);((InputMethodManager)current.getSystemService(Context.INPUT_METHOD_SERVICE)).showSoftInput(input,InputMethodManager.SHOW_IMPLICIT);});
        waitNavigation(false);UiTestCapture.save(getInstrumentation(),"08-keyboard-hidden-navigation");
        runTestOnUiThread(()->((InputMethodManager)current.getSystemService(Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(current.getWindow().getDecorView().getWindowToken(),0));waitNavigation(true);
    }
    @Override protected void tearDown()throws Exception {
        if(current!=null){getInstrumentation().runOnMainSync(()->current.finish());getInstrumentation().waitForIdleSync();}
        Context c=getInstrumentation().getTargetContext();c.getSharedPreferences("archive",0).edit().putString("active",oldRoot).commit();c.getSharedPreferences("appearance",0).edit().putString("theme",oldTheme).commit();if(root!=null)ArchiveService.remove(root);super.tearDown();
    }
}

package com.northcape.northdiary;

import android.app.Instrumentation;
import android.content.*;
import android.content.res.Configuration;
import android.graphics.Color;
import android.test.ActivityInstrumentationTestCase2;
import android.view.*;
import android.widget.*;
import java.io.File;
import java.util.UUID;
import static com.northcape.northdiary.Models.*;

/** Exercises actual theme-picker clicks, recreation, cold launch and persisted content. */
public class ThemeTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public ThemeTest(){super(MainActivity.class);}
    private MainActivity current;
    private String originalRoot,originalTheme;
    private File testRoot;
    private Article sample;
    @Override protected void setUp()throws Exception {
        super.setUp();Context c=getInstrumentation().getTargetContext();
        originalRoot=c.getSharedPreferences("archive",0).getString("active","store-initial");originalTheme=Appearance.choice(c);
        String name="theme-test-"+UUID.randomUUID();testRoot=new File(c.getFilesDir(),name);
        c.getSharedPreferences("archive",0).edit().putString("active",name).commit();
        c.getSharedPreferences("appearance",0).edit().putString("theme","light").commit();
        try(DiaryStore store=new DiaryStore(c,testRoot)){
            String[] titles={"秋日散步","写给未来的一封信","一些没有日期的片段"};
            for(int i=0;i<titles.length;i++){
                Article a=new Article();a.id=UUID.randomUUID().toString();a.title=titles[i];a.date="2026-10-"+(28+i);a.outside=i==2;
                a.text="留下一段普通日子里的小事，等未来某一天再翻开。";a.html="<p>"+a.text+"</p>";a.tags.add("日常");store.save(a);if(i==0)sample=a;
            }
            Person p=new Person();p.id=UUID.randomUUID().toString();p.name="林间";p.code="A01";store.savePerson(p);
        }
    }
    private View find(View view,String text){
        if(view instanceof TextView&&((TextView)view).getText().toString().equals(text))return view;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){View child=find(((ViewGroup)view).getChildAt(i),text);if(child!=null)return child;}return null;
    }
    private void clickText(String text)throws Throwable {
        runTestOnUiThread(()->{
            View view=find(current.getWindow().getDecorView(),text);assertNotNull(text,view);
            while(!view.hasOnClickListeners()&&view.getParent() instanceof View)view=(View)view.getParent();assertTrue(view.performClick());
        });getInstrumentation().waitForIdleSync();
    }
    private void choose(int index,String value)throws Throwable {
        clickText("界面主题");
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);getInstrumentation().addMonitor(monitor);
        runTestOnUiThread(()->{
            ListView choices=current.themeDialog.getListView();assertNotNull(choices);
            choices.performItemClick(choices.getAdapter().getView(index,null,choices),index,index);
        });
        current=(MainActivity)monitor.waitForActivityWithTimeout(10000);getInstrumentation().removeMonitor(monitor);assertNotNull("theme recreation must remain in app",current);
        getInstrumentation().waitForIdleSync();assertEquals(value,Appearance.choice(current));
        int mode=current.getResources().getConfiguration().uiMode&Configuration.UI_MODE_NIGHT_MASK;
        int expected=value.equals("system")?(getInstrumentation().getTargetContext().getResources().getConfiguration().uiMode&Configuration.UI_MODE_NIGHT_MASK)
            :value.equals("dark")?Configuration.UI_MODE_NIGHT_YES:Configuration.UI_MODE_NIGHT_NO;
        assertEquals(expected,mode);assertEquals(Color.parseColor(expected==Configuration.UI_MODE_NIGHT_YES?"#242222":"#F5F0E6"),current.getColor(R.color.paper));
        try(DiaryStore store=new DiaryStore(current,testRoot)){assertEquals(sample.title,store.get(sample.id).title);}
    }
    public void testThemePickerRecreationAndColdLaunch()throws Throwable {
        current=getActivity();getInstrumentation().waitForIdleSync();UiTestCapture.save(getInstrumentation(),"01-home-light");
        runTestOnUiThread(()->current.openArticle(sample.id,true));getInstrumentation().waitForIdleSync();UiTestCapture.save(getInstrumentation(),"02-editor-light");
        runTestOnUiThread(()->current.backFromArticle());getInstrumentation().waitForIdleSync();clickText("设置");choose(2,"dark");
        UiTestCapture.save(getInstrumentation(),"03-settings-dark");
        runTestOnUiThread(()->current.finish());getInstrumentation().waitForIdleSync();
        current=(MainActivity)getInstrumentation().startActivitySync(new Intent(getInstrumentation().getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        getInstrumentation().waitForIdleSync();assertEquals("dark",Appearance.choice(current));assertEquals(Color.parseColor("#242222"),current.getColor(R.color.paper));
        UiTestCapture.save(getInstrumentation(),"04-home-dark");clickText("设置");choose(1,"light");choose(0,"system");choose(2,"dark");choose(1,"light");
        clickText("人物");UiTestCapture.save(getInstrumentation(),"05-people-light");
    }
    @Override protected void tearDown()throws Exception {
        if(current!=null){getInstrumentation().runOnMainSync(()->current.finish());getInstrumentation().waitForIdleSync();}
        Context c=getInstrumentation().getTargetContext();c.getSharedPreferences("archive",0).edit().putString("active",originalRoot).commit();
        c.getSharedPreferences("appearance",0).edit().putString("theme",originalTheme).commit();if(testRoot!=null)ArchiveService.remove(testRoot);super.tearDown();
    }
}

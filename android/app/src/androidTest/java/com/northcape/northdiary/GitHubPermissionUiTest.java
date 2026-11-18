package com.northcape.northdiary;

import android.app.*;
import android.content.*;
import android.test.ActivityInstrumentationTestCase2;
import android.widget.*;
import java.io.File;
import java.util.*;

/** Real dialog close/reopen and recreation without accessing a real account or network. */
public class GitHubPermissionUiTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public GitHubPermissionUiTest(){super(MainActivity.class);}
    private MainActivity current;private File root;private String oldRoot;private Map<String,?> oldConfig;
    @Override protected void setUp()throws Exception{
        super.setUp();Context c=getInstrumentation().getTargetContext();oldRoot=c.getSharedPreferences("archive",0).getString("active","store-initial");oldConfig=new HashMap<>(c.getSharedPreferences("github-config",0).getAll());
        c.getSharedPreferences("github-config",0).edit().clear().commit();String name="github-permission-ui-"+UUID.randomUUID();root=new File(c.getFilesDir(),name);c.getSharedPreferences("archive",0).edit().putString("active",name).commit();
    }
    private CheckBox choice(){return current.githubDialog.dialog.getWindow().getDecorView().findViewWithTag("github-repository-access");}
    public void testChoiceSurvivesCloseReopenAndRecreationWithoutGrantingAccess()throws Throwable{
        current=getActivity();getInstrumentation().waitForIdleSync();String authorization=new GitHubCredentialStore(current).authorization(),login=new GitHubCredentialStore(current).login();
        runTestOnUiThread(()->{current.githubLogin();choice().setChecked(true);current.githubDialog.dialog.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();current.githubLogin();assertTrue(choice().isChecked());choice().setChecked(false);current.githubDialog.dismiss();current.githubLoginForPackages();assertFalse(choice().isChecked());choice().setChecked(true);current.githubDialog.dismiss();});
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(MainActivity.class.getName(),null,false);getInstrumentation().addMonitor(monitor);runTestOnUiThread(current::recreate);current=(MainActivity)monitor.waitForActivityWithTimeout(10000);getInstrumentation().removeMonitor(monitor);assertNotNull(current);getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{current.githubLogin();assertTrue(choice().isChecked());assertEquals(authorization,new GitHubCredentialStore(current).authorization());assertEquals(login,new GitHubCredentialStore(current).login());current.githubDialog.dismiss();});
    }
    public void testPermissionRepairPreservesRepositoryDraftWithoutInitializing()throws Throwable{
        current=getActivity();getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{
            current.githubTransferDialog=new GitHubTransferDialog(current,false);
            EditText repository=current.githubTransferDialog.dialog.getWindow().getDecorView().findViewWithTag("github-repository");repository.setText("qa/NorthDiary-Data");
            current.showWorkError(new GitHubPackagesApi.Failure("模拟仓库权限不足",404,true));assertTrue("Permission error must be visible",current.githubAccessError.isShowing());
            current.githubAccessError.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
        });
        // Native AlertDialog buttons dispatch their callbacks through the UI message queue.
        getInstrumentation().waitForIdleSync();
        runTestOnUiThread(()->{
            assertFalse("Transfer dialog closes before login",current.githubTransferDialog.dialog.isShowing());assertNotNull("Login dialog opens",current.githubDialog);assertTrue(current.githubDialog.dialog.isShowing());assertTrue("Repair requests repository access",choice().isChecked());
            current.githubDialog.dismiss();current.githubLogin();assertTrue("Default checked choice survives another entry point",choice().isChecked());
        });
        getInstrumentation().waitForIdleSync();UiTestCapture.save(getInstrumentation(),"17-github-permission-choice");
        runTestOnUiThread(()->{
            current.githubDialog.dismiss();current.githubTransferDialog=new GitHubTransferDialog(current,false);EditText restored=current.githubTransferDialog.dialog.getWindow().getDecorView().findViewWithTag("github-repository");assertEquals("qa/NorthDiary-Data",restored.getText().toString());assertEquals("",current.getSharedPreferences("github-config",0).getString("repository",""));current.githubTransferDialog.dismiss();
        });
    }

    @Override protected void tearDown()throws Exception{
        if(current!=null){getInstrumentation().runOnMainSync(()->current.finish());getInstrumentation().waitForIdleSync();}Context c=getInstrumentation().getTargetContext();c.getSharedPreferences("archive",0).edit().putString("active",oldRoot).commit();SharedPreferences.Editor edit=c.getSharedPreferences("github-config",0).edit().clear();
        for(Map.Entry<String,?> entry:oldConfig.entrySet()){Object v=entry.getValue();String k=entry.getKey();if(v instanceof String)edit.putString(k,(String)v);else if(v instanceof Boolean)edit.putBoolean(k,(Boolean)v);else if(v instanceof Integer)edit.putInt(k,(Integer)v);else if(v instanceof Long)edit.putLong(k,(Long)v);else if(v instanceof Float)edit.putFloat(k,(Float)v);}edit.commit();if(root!=null)ArchiveService.remove(root);super.tearDown();
    }
}

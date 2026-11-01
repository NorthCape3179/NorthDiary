package com.northcape.northdiary;

import android.app.AlertDialog;
import android.content.*;
import android.os.*;
import android.text.InputType;
import android.widget.*;
import java.util.concurrent.*;

/** Device authorization continues while the user visits the external GitHub browser. */
final class GitHubLoginDialog {
    private final MainActivity host;private final GitHubAuthApi api=new GitHubAuthApi();private final GitHubCredentialStore credentials;
    private final Handler handler=new Handler(Looper.getMainLooper());private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final EditText client,token;private final TextView state,code;private final Button start,connect;
    private AlertDialog dialog;private volatile int generation=0;private int interval;private long expires;private String activeClient="";private GitHubAuthApi.Challenge challenge;
    private volatile boolean closed=false;private boolean working=false;
    GitHubLoginDialog(MainActivity host){
        this.host=host;credentials=new GitHubCredentialStore(host);LinearLayout content=Ui.column(host);Ui.pad(content,20);
        content.addView(Ui.heading(host,"连接 GitHub"));Ui.gap(content,8);
        content.addView(Ui.text(host,"授权在 GitHub 官方页面完成。当前只连接账号，文章包交换尚未接入。",13,R.color.muted));Ui.gap(content,16);
        state=Ui.text(host,credentials.login().isEmpty()?"尚未登录":"已保存账号 @"+credentials.login(),14,R.color.accent);content.addView(state);
        Ui.section(content,"浏览器授权");
        client=Ui.input(host,"OAuth Client ID（与桌面端共用）",true);client.setText(host.getSharedPreferences("github-config",0).getString("client-id",""));content.addView(client);Ui.gap(content,8);
        content.addView(Ui.text(host,"首次填写自己的 OAuth 应用编号，并在 GitHub 应用设置中启用 Device Flow；不需要 Client Secret。",12,R.color.muted));Ui.gap(content,10);
        start=Ui.primary(host,"开始浏览器登录",this::start);content.addView(start);Ui.gap(content,10);
        code=Ui.text(host,"",23,R.color.accent);code.setTextIsSelectable(true);content.addView(code);
        content.addView(Ui.button(host,"复制验证码并打开 GitHub",()->{
            if(challenge==null){state.setText("请先开始浏览器登录。");return;}
            ((ClipboardManager)host.getSystemService(Context.CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("GitHub 设备验证码",challenge.userCode));
            ArticleText.open(host,"https://github.com/login/device");
        }));Ui.gap(content,8);content.addView(Ui.quiet(host,"OAuth 应用设置",()->ArticleText.open(host,"https://github.com/settings/developers")));
        Ui.section(content,"或使用专用访问令牌");
        token=Ui.input(host,"粘贴 GitHub Personal access token",true);token.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);content.addView(token);Ui.gap(content,10);
        connect=Ui.button(host,"使用令牌连接",()->verify(token.getText().toString().trim(),++generation));content.addView(connect);Ui.gap(content,14);
        content.addView(Ui.text(host,"登录凭据使用本机 Android Keystore 加密保存，不进入日记备份。此版本不自动上传文章。",11,R.color.muted));
        if(!credentials.login().isEmpty()){
            Ui.gap(content,14);content.addView(Ui.button(host,"重新验证已保存账号",()->{int id=++generation;job(id,()->api.user(credentials.token()),login->state.setText("已验证 @"+login));}));
            Ui.gap(content,8);content.addView(Ui.quiet(host,"退出本机登录",()->{cancel();try{credentials.clear();state.setText("已退出本机登录。GitHub 授权可在官网撤销。");host.refreshAccount();}catch(Exception e){Ui.error(host,e);}}));
        }
        dialog=new AlertDialog.Builder(host).setView(Ui.scroll(host,content)).setNegativeButton("关闭",(d,w)->{}).create();dialog.setOnDismissListener(d->close());dialog.show();
    }
    private interface Action<T>{T run()throws Exception;}private interface Result<T>{void accept(T value)throws Exception;}
    private <T> void job(int id,Action<T> action,Result<T> result){
        if(closed)return;working=true;buttons(false);
        worker.execute(()->{
            try{T value=action.run();handler.post(()->{if(closed||generation!=id)return;working=false;buttons(true);try{result.accept(value);}catch(Exception e){error(e);}});}
            catch(Exception e){handler.post(()->{if(closed||generation!=id)return;working=false;buttons(true);error(e);});}
        });
    }
    private void buttons(boolean enabled){start.setEnabled(enabled);connect.setEnabled(enabled);}
    private void error(Exception error){
        if(error instanceof org.json.JSONException){state.setText("GitHub 响应格式异常，请重试。");return;}
        if(error instanceof java.security.GeneralSecurityException){state.setText("本机加密存储暂不可用，请重试。");return;}
        state.setText(error instanceof java.net.SocketTimeoutException?"GitHub 连接超时，请检查网络后重试。":error.getMessage()==null?"连接失败，请重试。":error.getMessage());
    }
    private synchronized void cancel(){generation++;handler.removeCallbacksAndMessages(null);challenge=null;code.setText("");working=false;buttons(true);}
    private void start(){
        if(working)return;cancel();int id=generation;activeClient=client.getText().toString().trim();state.setText("正在申请验证码…");
        host.getSharedPreferences("github-config",0).edit().putString("client-id",activeClient).apply();
        job(id,()->api.start(activeClient),value->{challenge=value;interval=value.interval;expires=SystemClock.elapsedRealtime()+value.expires*1000L;code.setText(value.userCode);state.setText("打开 GitHub，输入验证码并授权。等待授权中…");schedule(id);});
    }
    private void schedule(int id){handler.postDelayed(()->poll(id),interval*1000L);}
    private void poll(int id){
        if(closed||generation!=id||challenge==null)return;
        if(SystemClock.elapsedRealtime()>=expires){state.setText("验证码已过期，请重新开始。");challenge=null;return;}
        GitHubAuthApi.Challenge current=challenge;
        job(id,()->api.poll(activeClient,current),result->{
            if(result.state.equals("connected")){verify(result.token,id);return;}
            if(result.state.equals("slow_down"))interval=Math.min(60,interval+5);schedule(id);
        });
    }
    private void verify(String value,int id){
        handler.removeCallbacksAndMessages(null);state.setText("正在验证 GitHub 账号…");
        job(id,()->{String login=api.user(value);synchronized(this){if(closed||generation!=id)throw new CancellationException();credentials.save(value,login);}return login;},login->{challenge=null;code.setText("");token.getText().clear();state.setText("已连接 @"+login+"。当前尚未开启文章同步。");host.refreshAccount();});
    }
    void dismiss(){if(dialog!=null)dialog.dismiss();}
    private synchronized void close(){if(closed)return;closed=true;generation++;handler.removeCallbacksAndMessages(null);worker.shutdownNow();}
}

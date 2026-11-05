package com.northcape.northdiary;

import android.app.AlertDialog;
import android.widget.*;
import java.util.*;

/** Manual private-repository transfer; remote files are imported only after preview. */
final class GitHubTransferDialog {
    private final MainActivity host;
    private final EditText repository;
    private final TextView state;
    private final ListView list;
    private final List<GitHubPackagesApi.Package> packages=new ArrayList<>();
    private String loadedRepository="";
    final AlertDialog dialog;
    AlertDialog initializationDialog;
    GitHubTransferDialog(MainActivity host,boolean refresh){
        this.host=host;LinearLayout content=Ui.column(host);Ui.pad(content,20);content.setBackgroundColor(Ui.color(host,R.color.card));
        content.addView(Ui.heading(host,"GitHub 文集"));Ui.gap(content,8);content.addView(Ui.text(host,"独立私有数据仓库 · 手动上传/下载文集，每包最多 20 MiB。",12,R.color.muted));Ui.gap(content,12);
        GitHubCredentialStore credentials=new GitHubCredentialStore(host);String login=credentials.login();content.addView(Ui.text(host,login.isEmpty()?"尚未登录":"当前账号 @"+login+"\n"+credentials.authorizationLabel(),13,R.color.accent));
        content.addView(Ui.button(host,"登录或调整仓库权限",()->{dismiss();host.githubLoginForPackages();}));Ui.gap(content,12);
        repository=Ui.input(host,"账号/私有数据仓库名",true);repository.setTag("github-repository");repository.setText(host.getSharedPreferences("github-config",0).getString("repository-draft",host.getSharedPreferences("github-config",0).getString("repository","")));content.addView(repository);Ui.gap(content,8);
        content.addView(Ui.text(host,"已有桌面数据仓库可直接连接。首次使用时，先在 GitHub 新建空的 Private 仓库，例如 NorthDiary-Data，再初始化。",12,R.color.muted));Ui.gap(content,10);
        LinearLayout setup=Ui.row(host);Ui.weighted(setup,Ui.button(host,"连接已有仓库",this::connect),1);Ui.weighted(setup,Ui.quiet(host,"初始化空仓库",this::initialize),1);content.addView(setup);Ui.gap(content,8);
        content.addView(Ui.quiet(host,"打开 GitHub 新建仓库页面",()->ArticleText.open(host,"https://github.com/new")));Ui.gap(content,12);
        content.addView(Ui.primary(host,"选择文章并导出到 GitHub",()->host.startGitHubExport(repository.getText().toString().trim())));Ui.gap(content,8);
        content.addView(Ui.button(host,"刷新远端文集",this::load));Ui.gap(content,8);
        state=Ui.text(host,"连接仓库后，点击远端文集即可下载并预览导入。",12,R.color.muted);content.addView(state);Ui.gap(content,8);
        list=new ListView(host);list.setTag("github-packages");content.addView(list,new LinearLayout.LayoutParams(-1,Ui.dp(host,220)));render();
        list.setOnItemClickListener((p,v,i,id)->{GitHubPackagesApi.Package pack=packages.get(i);String repo=loadedRepository;host.work("下载并检查文集",()->{
            java.io.File file=host.githubPackages().download(repo,pack);try(java.io.InputStream in=new java.io.FileInputStream(file)){return EpubImportService.prepare(host,host.diaryStore(),in);}finally{file.delete();}
        },preview->{dismiss();host.showImportPreview(preview);});});
        Ui.watch(repository,()->{host.getSharedPreferences("github-config",0).edit().putString("repository-draft",repository.getText().toString().trim()).apply();packages.clear();loadedRepository="";render();state.setText("仓库名称已修改，请重新连接或刷新。");});
        dialog=new AlertDialog.Builder(host).setView(Ui.scroll(host,content)).setNegativeButton("关闭",null).create();dialog.show();
        if(refresh&&!repository.getText().toString().trim().isEmpty()&&!login.isEmpty())load();
    }
    private void saveRepository(String name)throws Exception{if(!host.getSharedPreferences("github-config",0).edit().putString("repository",name).putString("repository-draft",name).commit())throw new java.io.IOException("仓库设置保存失败，请重试");}
    private void connect(){String name=repository.getText().toString().trim();host.work("连接私有数据仓库",()->host.githubPackages().checkRepository(name),repo->{saveRepository(repo.name);state.setText("已连接 "+repo.name+"，可刷新远端列表并按账号权限导入/导出。");});}
    private void initialize(){
        String name=repository.getText().toString().trim();try{GitHubPackagesApi.repositoryName(name);}catch(Exception e){Ui.error(host,e);return;}
        initializationDialog=new AlertDialog.Builder(host).setTitle("初始化空的私有仓库").setMessage(name+"\n\n仅适用于空仓库；会添加 NorthDiary 数据标识。")
            .setPositiveButton("确认初始化",(d,w)->host.work("初始化数据仓库",()->host.githubPackages().initializeRepository(name),repo->{saveRepository(repo.name);state.setText("已初始化 "+repo.name+"，可以开始上传文集。");})).setNegativeButton("取消",null).show();
    }
    private void load(){String name=repository.getText().toString().trim();host.work("读取远端文集",()->host.githubPackages().list(name),rows->{saveRepository(name);loadedRepository=name;packages.clear();packages.addAll(rows);render();state.setText(rows.isEmpty()?"远端还没有文集，可先选择文章并导出。":"已读取 "+rows.size()+" 个文集，点击一行下载并预览导入。");});}
    private void render(){List<String> labels=new ArrayList<>();for(GitHubPackagesApi.Package p:packages){String n=p.name;labels.add(n.substring(0,4)+"-"+n.substring(4,6)+"-"+n.substring(6,8)+" "+n.substring(9,11)+":"+n.substring(11,13)+":"+n.substring(13,15)+" UTC\n"+String.format(Locale.ROOT,"%.2f MiB",p.size/1048576.0)+" · "+n.substring(n.indexOf('-')+1,n.indexOf('-')+9));}list.setAdapter(new ArrayAdapter<>(host,android.R.layout.simple_list_item_1,labels));}
    void dismiss(){if(initializationDialog!=null)initializationDialog.dismiss();if(dialog!=null)dialog.dismiss();}
}

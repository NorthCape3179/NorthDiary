package com.northcape.northdiary;

import android.view.*;
import android.widget.*;

final class SettingsPanel extends ScrollView {
    SettingsPanel(MainActivity host,DiaryStore store){
        super(host);setFillViewport(true);setVerticalScrollBarEnabled(false);
        FrameLayout frame=new FrameLayout(host);addView(frame);
        LinearLayout content=Ui.column(host);Ui.pad(content,20);
        int width=Math.min(Ui.dp(host,680),Ui.dp(host,host.getResources().getConfiguration().screenWidthDp));
        frame.addView(content,new FrameLayout.LayoutParams(width,-2,Gravity.TOP|Gravity.CENTER_HORIZONTAL));
        content.addView(Ui.heading(host,"设置"));Ui.gap(content,7);content.addView(Ui.text(host,"让记录更贴近你的习惯。",13,R.color.muted));
        Ui.section(content,"外观");
        content.addView(Ui.setting(host,"moon","界面主题",Appearance.label(host),host::showThemePicker));
        Ui.section(content,"GitHub 文集");String login=new GitHubCredentialStore(host).login();
        content.addView(Ui.setting(host,"link","GitHub 登录",login.isEmpty()?"浏览器授权或专用令牌":"已保存 @"+login,host::githubLogin));Ui.gap(content,10);
        String repository=host.getSharedPreferences("github-config",0).getString("repository","");
        content.addView(Ui.setting(host,"archive","私有数据仓库",repository.isEmpty()?"连接或初始化独立的私有仓库":repository,host::githubTransfers));Ui.gap(content,10);
        content.addView(Ui.setting(host,"backup","导出到 GitHub","选择文章，上传原生 EPUB 文集",host::githubExport));Ui.gap(content,10);
        content.addView(Ui.setting(host,"restore","从 GitHub 导入","下载远端文集，检查并预览后合并",host::githubTransfers));
        Ui.section(content,"数据与备份");
        content.addView(Ui.setting(host,"book","导出 EPUB 文集","按分类或标签选文章，生成阅读用电子书",host::exportEpub));Ui.gap(content,10);
        content.addView(Ui.setting(host,"restore","导入 NorthDiary EPUB","预览后合并文章；重复跳过，冲突保留副本",host::importEpub));Ui.gap(content,10);
        content.addView(Ui.setting(host,"backup","导出完整备份","保存文章、人物、标签与图片",host::exportBackup));Ui.gap(content,10);
        content.addView(Ui.setting(host,"restore","从备份恢复","检查完整档案后切换，保留恢复前数据",host::requestRestore));
        String previous=host.getSharedPreferences("archive",0).getString("previous",null);
        if(previous!=null){Ui.gap(content,10);content.addView(Ui.setting(host,"restore","切回恢复前档案","返回上一次切换前的记录",()->host.previousArchive(previous)));}
        Ui.section(content,"关于 NORTHDIARY");
        LinearLayout about=Ui.column(host);Ui.card(about);about.addView(Ui.text(host,"记录时间，留存记忆。",18,R.color.ink));Ui.gap(about,9);
        about.addView(Ui.text(host,"一个安静的地方，收藏往事、人物，\n和不必归属于某一天的记忆。",14,R.color.muted));Ui.gap(about,18);
        about.addView(Ui.text(host,"Android 0.1.5-alpha  ·  本地记忆档案馆",11,R.color.accent));content.addView(about);Ui.gap(content,10);
        content.addView(Ui.setting(host,"book","源码与许可证","AGPL-3.0-or-later",()->ArticleText.open(host,"https://github.com/NorthCape3179/NorthDiary/tree/android/v0.1-alpha/android")));
        Ui.gap(content,20);TextView scope=Ui.text(host,"GitHub 使用独立私有仓库，手动上传或下载 NorthDiary EPUB 文集；每包最多 20 MiB。下载后先预览，重复跳过，冲突另存副本。\n\n本地 EPUB 支持桌面端或安卓 0.1.4+ 的数据清单；普通 EPUB、安卓 0.1.3 阅读版文集暂不支持导入。复杂桌面排版会简化；图片仍为文件名链接。文集支持 PNG、JPEG、GIF；单图最多 32 MiB，本地文集与备份最多 200 MiB。",12,R.color.muted);scope.setLineSpacing(Ui.dp(host,3),1.1f);content.addView(scope);Ui.gap(content,12);
    }
}

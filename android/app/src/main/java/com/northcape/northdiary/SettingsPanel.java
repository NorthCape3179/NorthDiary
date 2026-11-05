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
        Ui.section(content,"账号");String login=new GitHubCredentialStore(host).login();
        content.addView(Ui.setting(host,"link","GitHub 登录",login.isEmpty()?"浏览器授权或专用令牌 · 文章同步尚未接入":"已保存 @"+login,host::githubLogin));
        Ui.section(content,"数据与备份");
        content.addView(Ui.setting(host,"book","导出 EPUB 文集","按分类或标签选文章，生成阅读用电子书",host::exportEpub));Ui.gap(content,10);
        content.addView(Ui.setting(host,"backup","导出完整备份","保存文章、人物、标签与图片",host::exportBackup));Ui.gap(content,10);
        content.addView(Ui.setting(host,"restore","从备份恢复","检查完整档案后切换，保留恢复前数据",host::requestRestore));
        String previous=host.getSharedPreferences("archive",0).getString("previous",null);
        if(previous!=null){Ui.gap(content,10);content.addView(Ui.setting(host,"restore","切回恢复前档案","返回上一次切换前的记录",()->host.previousArchive(previous)));}
        Ui.section(content,"关于 NORTHDIARY");
        LinearLayout about=Ui.column(host);Ui.card(about);about.addView(Ui.text(host,"记录时间，留存记忆。",18,R.color.ink));Ui.gap(about,9);
        about.addView(Ui.text(host,"一个安静的地方，收藏往事、人物，\n和不必归属于某一天的记忆。",14,R.color.muted));Ui.gap(about,18);
        about.addView(Ui.text(host,"Android 0.1.3-alpha  ·  本地记忆档案馆",11,R.color.accent));content.addView(about);Ui.gap(content,10);
        content.addView(Ui.setting(host,"book","源码与许可证","AGPL-3.0-or-later",()->ArticleText.open(host,"https://github.com/NorthCape3179/NorthDiary/tree/android/v0.1-alpha/android")));
        Ui.gap(content,20);TextView scope=Ui.text(host,"支持本地记录、分类、随机回忆、EPUB 阅读文集与完整备份。GitHub 当前仅支持账号登录，文章同步和 EPUB 导入尚未接入。\n\nEPUB 保留基础段落、加粗、斜体、居中与图片文件名链接；复杂桌面排版会简化。文集目前仅支持 PNG、JPEG、GIF 附件。单张图片最多 32 MiB；文集与备份最多 200 MiB。",12,R.color.muted);scope.setLineSpacing(Ui.dp(host,3),1.1f);content.addView(scope);Ui.gap(content,12);
    }
}

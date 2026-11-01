package com.northcape.northdiary;

import android.content.Context;
import android.content.res.Configuration;

/** Resolve the selected palette before Activity/Window obtains themed resources. */
final class Appearance {
    static String choice(Context context) {
        return context.getSharedPreferences("appearance",0).getString("theme","system");
    }
    static Context wrap(Context base) {
        String choice=choice(base);
        if(!choice.equals("dark")&&!choice.equals("light")&&!choice.equals("forest"))return base;
        Configuration config=new Configuration(base.getResources().getConfiguration());
        config.uiMode=(config.uiMode & ~Configuration.UI_MODE_NIGHT_MASK)
            | ((choice.equals("dark")||choice.equals("forest"))?Configuration.UI_MODE_NIGHT_YES:Configuration.UI_MODE_NIGHT_NO);
        return base.createConfigurationContext(config);
    }
    static String label(Context context) {
        switch(choice(context)) {
            case "forest":return "深色 · 森林绿";
            case "dark":return "深色 · 暮色酒红";
            case "light":return "浅色 · 米色与红酒";
            default:return "跟随系统";
        }
    }
}

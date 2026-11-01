package com.northcape.northdiary;

import android.app.Activity;
import android.graphics.Rect;
import android.os.Build;
import android.view.*;

/** Apply system/IME space once and hide app navigation while the IME is visible. */
final class KeyboardInsets {
    static void bind(Activity activity,View root,View navigation){
        navigation.setTag("bottom-navigation");
        if(Build.VERSION.SDK_INT>=30){
            activity.getWindow().setDecorFitsSystemWindows(false);
            root.setOnApplyWindowInsetsListener((view,insets)->{
                boolean keyboard=insets.isVisible(WindowInsets.Type.ime());
                navigation.setVisibility(keyboard?View.GONE:View.VISIBLE);
                android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout()|WindowInsets.Type.ime());
                view.setPadding(safe.left,safe.top,safe.right,safe.bottom);return insets;
            });
        }else{
            root.getViewTreeObserver().addOnGlobalLayoutListener(()->{
                Rect visible=new Rect();root.getWindowVisibleDisplayFrame(visible);
                int height=root.getRootView().getHeight();boolean keyboard=height-visible.bottom>Math.max(Ui.dp(activity,120),height/5);
                int state=keyboard?View.GONE:View.VISIBLE;if(navigation.getVisibility()!=state)navigation.setVisibility(state);
            });
        }
        root.requestApplyInsets();
    }
    private KeyboardInsets(){}
}

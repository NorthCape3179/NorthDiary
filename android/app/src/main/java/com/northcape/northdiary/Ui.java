package com.northcape.northdiary;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.*;
import android.text.*;
import android.view.*;
import android.widget.*;

final class Ui {
    static int dp(Context c,float n){return (int)(c.getResources().getDisplayMetrics().density*n+0.5f);}
    static boolean compact(Context c){return c.getResources().getConfiguration().screenHeightDp<480;}
    static LinearLayout column(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.VERTICAL);return l;}
    static LinearLayout row(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    static void pad(View v,int n){int p=dp(v.getContext(),n);v.setPadding(p,p,p,p);}
    static TextView text(Context c,String text,int size,int color){TextView t=new TextView(c);t.setText(text);t.setTextSize(size);t.setTextColor(c.getColor(color));t.setFontFeatureSettings("kern");t.setLineSpacing(dp(c,2),1.05f);return t;}
    static TextView heading(Context c,String text){TextView t=text(c,text,24,R.color.ink);t.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));return t;}
    static GradientDrawable surface(Context c,int color,float radius,boolean border){GradientDrawable d=new GradientDrawable();d.setColor(c.getColor(color));d.setCornerRadius(dp(c,radius));if(border)d.setStroke(dp(c,1),c.getColor(R.color.line));return d;}
    static Drawable ripple(Context c,int color,float radius,boolean border){return new RippleDrawable(ColorStateList.valueOf(c.getColor(R.color.ripple)),surface(c,color,radius,border),surface(c,R.color.ink,radius,false));}
    static Button button(Context c,String label,Runnable action){
        Button b=new Button(c);b.setText(label);b.setTextSize(14);b.setAllCaps(false);b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        b.setTextColor(c.getColor(R.color.accent));b.setBackground(ripple(c,R.color.soft,14,false));b.setStateListAnimator(null);
        b.setMinWidth(0);b.setMinimumWidth(0);b.setMinHeight(dp(c,44));b.setMinimumHeight(dp(c,44));b.setPadding(dp(c,14),dp(c,8),dp(c,14),dp(c,8));
        b.setOnClickListener(v->action.run());return b;
    }
    static Button primary(Context c,String label,Runnable action){Button b=button(c,label,action);b.setTextColor(c.getColor(R.color.on_accent));b.setBackground(ripple(c,R.color.accent,14,false));return b;}
    static Button quiet(Context c,String label,Runnable action){Button b=button(c,label,action);b.setTextColor(c.getColor(R.color.muted));b.setBackground(ripple(c,R.color.paper,14,false));return b;}
    static EditText input(Context c,String hint,boolean single){
        EditText e=new EditText(c);e.setHint(hint);e.setTextSize(15);e.setTextColor(c.getColor(R.color.ink));e.setHintTextColor(c.getColor(R.color.muted));
        e.setSingleLine(single);e.setBackground(surface(c,R.color.card,14,true));e.setPadding(dp(c,14),dp(c,12),dp(c,14),dp(c,12));e.setMinHeight(dp(c,48));return e;
    }
    static EditText search(Context c,String hint){EditText e=input(c,hint,true);ArchiveIcon.Glyph icon=new ArchiveIcon.Glyph("search",c.getColor(R.color.muted));icon.setBounds(0,0,dp(c,19),dp(c,19));e.setCompoundDrawables(icon,null,null,null);e.setCompoundDrawablePadding(dp(c,10));e.setTextSize(14);return e;}
    static void watch(EditText e,Runnable changed){e.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int n,int f){}public void onTextChanged(CharSequence s,int a,int n,int f){changed.run();}public void afterTextChanged(Editable s){}});}
    static void card(View view){view.setBackground(surface(view.getContext(),R.color.card,20,true));pad(view,18);}
    static ScrollView scroll(Context c,View child){ScrollView s=new ScrollView(c);s.setFillViewport(true);s.setClipToPadding(false);s.addView(child);return s;}
    static HorizontalScrollView horizontal(Context c,View child){HorizontalScrollView s=new HorizontalScrollView(c);s.setHorizontalScrollBarEnabled(false);s.addView(child);return s;}
    static void weighted(LinearLayout row,View child,float weight){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,weight);p.setMargins(dp(row.getContext(),3),0,dp(row.getContext(),3),0);row.addView(child,p);}
    static void gap(LinearLayout parent,int height){View v=new View(parent.getContext());parent.addView(v,new LinearLayout.LayoutParams(1,dp(parent.getContext(),height)));}
    static void section(LinearLayout parent,String title){gap(parent,22);TextView text=text(parent.getContext(),title,12,R.color.muted);text.setLetterSpacing(.10f);parent.addView(text);gap(parent,10);}
    static View setting(Context c,String icon,String title,String subtitle,Runnable action){
        LinearLayout item=row(c);item.setBackground(ripple(c,R.color.card,18,true));pad(item,16);item.setMinimumHeight(dp(c,80));
        LinearLayout mark=row(c);mark.setGravity(Gravity.CENTER);mark.setBackground(surface(c,R.color.soft,13,false));mark.addView(new ArchiveIcon(c,icon,R.color.accent,22));
        item.addView(mark,new LinearLayout.LayoutParams(dp(c,42),dp(c,42)));
        LinearLayout labels=column(c);labels.setPadding(dp(c,14),0,dp(c,12),0);labels.addView(text(c,title,16,R.color.ink));gap(labels,5);labels.addView(text(c,subtitle,12,R.color.muted));
        item.addView(labels,new LinearLayout.LayoutParams(0,-2,1));item.addView(new ArchiveIcon(c,"arrow",R.color.muted,18));
        item.setOnClickListener(v->action.run());item.setFocusable(true);item.setContentDescription(title+"，"+subtitle);return item;
    }
    static View empty(Context c,String title,String detail,String action,Runnable click){
        LinearLayout box=column(c);box.setGravity(Gravity.CENTER);pad(box,24);
        if(compact(c)){box.addView(text(c,title,16,R.color.muted));return box;}
        LinearLayout icon=row(c);icon.setGravity(Gravity.CENTER);icon.setBackground(surface(c,R.color.soft,26,false));icon.addView(new ArchiveIcon(c,"archive",R.color.accent,36));
        box.addView(icon,new LinearLayout.LayoutParams(dp(c,80),dp(c,80)));gap(box,22);
        TextView h=heading(c,title);h.setTextSize(20);h.setGravity(Gravity.CENTER);box.addView(h);gap(box,10);
        TextView hint=text(c,detail,14,R.color.muted);hint.setGravity(Gravity.CENTER);box.addView(hint);gap(box,22);
        if(action!=null)box.addView(primary(c,action,click));return box;
    }
    static View navigation(Context c,int selected,java.util.function.IntConsumer click){
        LinearLayout nav=row(c);nav.setBackground(surface(c,R.color.card,24,true));pad(nav,5);
        String[] labels={"记忆","人物","设置"},icons={"archive","people","settings"};
        for(int i=0;i<3;i++){
            final int tab=i;boolean active=i==selected;LinearLayout item=column(c);item.setGravity(Gravity.CENTER);item.setPadding(0,dp(c,8),0,dp(c,8));
            item.setBackground(ripple(c,active?R.color.soft:R.color.card,18,false));item.addView(new ArchiveIcon(c,icons[i],active?R.color.accent:R.color.muted,22));gap(item,4);
            TextView caption=text(c,labels[i],11,active?R.color.accent:R.color.muted);caption.setGravity(Gravity.CENTER);item.addView(caption);item.setOnClickListener(v->click.accept(tab));item.setFocusable(true);item.setContentDescription(labels[i]);item.setSelected(active);
            nav.addView(item,new LinearLayout.LayoutParams(0,-2,1));
        }return nav;
    }
    static void error(Context c,Exception e){new android.app.AlertDialog.Builder(c).setTitle("操作未完成").setMessage(e.getMessage()==null?e.getClass().getSimpleName():e.getMessage()).setPositiveButton("知道了",null).show();}
}

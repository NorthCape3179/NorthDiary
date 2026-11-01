package com.northcape.northdiary;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.text.*;
import android.view.*;
import android.widget.*;

final class Ui {
    static int dp(Context c,float n){return (int)(c.getResources().getDisplayMetrics().density*n+0.5f);}
    static LinearLayout column(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.VERTICAL);return l;}
    static LinearLayout row(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    static void pad(View v,int n){int p=dp(v.getContext(),n);v.setPadding(p,p,p,p);}
    static TextView text(Context c,String text,int size,int color){TextView t=new TextView(c);t.setText(text);t.setTextSize(size);t.setTextColor(c.getColor(color));t.setPadding(0,dp(c,8),0,dp(c,8));return t;}
    static TextView heading(Context c,String text){TextView t=text(c,text,24,R.color.ink);t.setTypeface(null,Typeface.BOLD);return t;}
    static Button button(Context c,String label,Runnable action){Button b=new Button(c);b.setText(label);b.setAllCaps(false);b.setOnClickListener(v->action.run());return b;}
    static EditText input(Context c,String hint,boolean single){EditText e=new EditText(c);e.setHint(hint);e.setTextColor(c.getColor(R.color.ink));e.setHintTextColor(c.getColor(R.color.muted));e.setSingleLine(single);return e;}
    static void watch(EditText e,Runnable changed){e.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int n,int f){}public void onTextChanged(CharSequence s,int a,int n,int f){changed.run();}public void afterTextChanged(Editable s){}});}
    static void card(View view){GradientDrawable d=new GradientDrawable();d.setColor(view.getContext().getColor(R.color.card));d.setCornerRadius(dp(view.getContext(),16));view.setBackground(d);pad(view,16);}
    static ScrollView scroll(Context c,View child){ScrollView s=new ScrollView(c);s.setFillViewport(true);s.addView(child);return s;}
    static HorizontalScrollView horizontal(Context c,View child){HorizontalScrollView s=new HorizontalScrollView(c);s.setHorizontalScrollBarEnabled(false);s.addView(child);return s;}
    static void weighted(LinearLayout row,View child,float weight){row.addView(child,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,weight));}
    static void error(Context c,Exception e){new android.app.AlertDialog.Builder(c).setTitle("操作未完成").setMessage(e.getMessage()==null?e.getClass().getSimpleName():e.getMessage()).setPositiveButton("知道了",null).show();}
}

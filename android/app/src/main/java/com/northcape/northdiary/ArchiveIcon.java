package com.northcape.northdiary;

import android.content.Context;
import android.graphics.*;
import android.graphics.drawable.Drawable;
import android.view.View;

/** Small, consistent native line icons. */
final class ArchiveIcon extends View {
    private final Glyph glyph;
    ArchiveIcon(Context c,String name,int color,int size) {
        super(c);glyph=new Glyph(name,Ui.color(c,color));
        setLayoutParams(new android.widget.LinearLayout.LayoutParams(Ui.dp(c,size),Ui.dp(c,size)));
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
    }
    @Override protected void onDraw(Canvas canvas){glyph.setBounds(0,0,getWidth(),getHeight());glyph.draw(canvas);}
    static final class Glyph extends Drawable {
        final String name; final Paint paint=new Paint(3);
        Glyph(String name,int color){this.name=name;paint.setColor(color);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.6f);paint.setStrokeCap(Paint.Cap.ROUND);paint.setStrokeJoin(Paint.Join.ROUND);}
        private void line(Canvas c,float x,float y,float xx,float yy){c.drawLine(x,y,xx,yy,paint);}
        @Override public void draw(Canvas c) {
            int save=c.save();c.translate(getBounds().left,getBounds().top);c.scale(getBounds().width()/24f,getBounds().height()/24f);
            switch(name) {
                case "timeline":line(c,6,3,6,21);for(int y:new int[]{5,12,19}){c.drawCircle(6,y,2,paint);line(c,12,y,21,y);}break;
                case "search":c.drawCircle(10,10,6,paint);line(c,14.5f,14.5f,20,20);break;
                case "people":c.drawCircle(9,8,3,paint);c.drawArc(3,13,15,24,180,180,false,paint);c.drawArc(13,5,21,13,270,180,false,paint);c.drawArc(12,14,23,24,280,80,false,paint);break;
                case "settings":c.drawCircle(12,12,4,paint);for(int i=0;i<8;i++){c.save();c.rotate(i*45,12,12);line(c,12,2.5f,12,5);c.restore();}c.drawCircle(12,12,8,paint);break;
                case "moon":c.drawArc(4,3,21,21,70,275,false,paint);c.drawArc(9,1,24,17,110,150,false,paint);break;
                case "backup":c.drawRoundRect(4,10,20,21,2,2,paint);line(c,12,16,12,3);line(c,8,7,12,3);line(c,12,3,16,7);break;
                case "restore":c.drawArc(4,4,21,21,200,300,false,paint);line(c,3,4,3,10);line(c,3,10,9,10);line(c,12,8,12,13);line(c,12,13,16,15);break;
                case "arrow":line(c,9,6,15,12);line(c,15,12,9,18);break;
                case "plus":line(c,12,5,12,19);line(c,5,12,19,12);break;
                case "check":line(c,5,12,10,17);line(c,10,17,20,7);break;
                case "link":c.drawArc(2,8,14,18,60,280,false,paint);c.drawArc(10,6,22,16,240,280,false,paint);line(c,8,14,16,10);break;
                case "book":c.drawRoundRect(4,3,20,21,2,2,paint);line(c,8,3,8,21);line(c,12,8,16,8);line(c,12,12,16,12);break;
                case "compass":c.drawCircle(12,12,9,paint);Path p=new Path();p.moveTo(15,6);p.lineTo(14,14);p.lineTo(6,17);p.lineTo(10,10);p.close();c.drawPath(p,paint);break;
                default:c.drawRoundRect(3,6,21,21,2,2,paint);line(c,3,11,21,11);line(c,9,15,15,15);line(c,7,3,17,3);break;
            }
            c.restoreToCount(save);
        }
        @Override public void setAlpha(int alpha){paint.setAlpha(alpha);}
        @Override public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);}
        @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    }
}

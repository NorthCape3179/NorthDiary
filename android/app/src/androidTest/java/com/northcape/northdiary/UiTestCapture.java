package com.northcape.northdiary;

import android.app.Instrumentation;
import android.content.*;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Build;
import android.provider.MediaStore;
import java.io.*;

/** Fictional emulator-only screenshots survive test app cleanup. */
final class UiTestCapture {
    static void save(Instrumentation instrumentation,String name)throws Exception{
        if(Build.VERSION.SDK_INT<29)return;
        instrumentation.waitForIdleSync();
        Thread.sleep(500); // Allow popup dim layers and the next rendered frame to settle.
        Bitmap bitmap=instrumentation.getUiAutomation().takeScreenshot();
        if(bitmap==null)throw new IOException("无法采集验证截图");
        ContentResolver resolver=instrumentation.getTargetContext().getContentResolver();
        ContentValues values=new ContentValues();values.put(MediaStore.Images.Media.DISPLAY_NAME,name+".png");values.put(MediaStore.Images.Media.MIME_TYPE,"image/png");
        values.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/NorthDiaryQA");values.put(MediaStore.Images.Media.IS_PENDING,1);
        Uri uri=resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);
        if(uri==null)throw new IOException("无法保存验证截图");
        try(OutputStream out=resolver.openOutputStream(uri)){
            if(out==null||!bitmap.compress(Bitmap.CompressFormat.PNG,100,out))throw new IOException("验证截图写入失败");
        }finally{bitmap.recycle();}
        values.clear();values.put(MediaStore.Images.Media.IS_PENDING,0);resolver.update(uri,values,null,null);
    }
}

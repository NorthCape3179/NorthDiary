package com.northcape.northdiary;

import android.util.AtomicFile;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static com.northcape.northdiary.Models.*;

/** Separate durable edit journal: invalid dates and failed database writes remain recoverable. */
final class DraftStore {
    private final AtomicFile file;
    DraftStore(File root) { file=new AtomicFile(new File(root,"mobile-edit.json")); }
    void write(Article a) throws Exception {
        JSONObject j=new JSONObject();
        j.put("id",a.id).put("title",a.title).put("date",a.date).put("html",a.html).put("text",a.text)
            .put("created",a.created).put("outside",a.outside).put("draft",a.draft)
            .put("tags",new JSONArray(a.tags)).put("people",new JSONArray(a.people));
        if(a.categories!=null)j.put("categories",new JSONArray(a.categories));
        FileOutputStream out=null;
        try { out=file.startWrite(); out.write(j.toString().getBytes(StandardCharsets.UTF_8)); file.finishWrite(out); }
        catch(Exception e) { if(out!=null) file.failWrite(out); throw e; }
    }
    Article read() throws Exception {
        JSONObject j;
        try(InputStream in=file.openRead()) { j=new JSONObject(new String(DiaryStore.readBytes(in,16*1024*1024),StandardCharsets.UTF_8)); }
        catch(FileNotFoundException e){return null;}
        Article a=new Article(); a.id=j.getString("id"); a.title=j.getString("title"); a.date=j.getString("date");
        a.html=j.getString("html"); a.text=j.getString("text"); a.created=j.getString("created"); a.outside=j.getBoolean("outside"); a.draft=j.getBoolean("draft");
        a.tags=array(j.getJSONArray("tags")); a.people=array(j.getJSONArray("people"));
        a.categories=j.has("categories")?array(j.getJSONArray("categories")):null;return a;
    }
    private static List<String> array(JSONArray j) throws JSONException { List<String> list=new ArrayList<>(); for(int i=0;i<j.length();i++)list.add(j.getString(i)); return list; }
    void clear() { file.delete(); }
}

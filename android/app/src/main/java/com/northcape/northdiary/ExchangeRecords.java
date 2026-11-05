package com.northcape.northdiary;

import android.database.Cursor;
import android.util.JsonReader;
import android.util.JsonToken;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.*;
import java.util.*;

/** Versioned desktop-compatible EPUB records and stable identities. */
final class ExchangeRecords {
    static final String PATH="EPUB/northdiary/manifest.json",FORMAT="NorthDiary-EPUB";
    static JSONObject parse(String json)throws Exception{
        try(JsonReader reader=new JsonReader(new StringReader(json))){reader.setLenient(false);Object value=read(reader,0,new int[]{0});require(reader.peek()==JsonToken.END_DOCUMENT&&value instanceof JSONObject,"导入清单无效");return (JSONObject)value;}
    }
    private static Object read(JsonReader reader,int depth,int[] items)throws Exception{
        require(depth<=32&&++items[0]<=200000,"导入清单过于复杂");
        switch(reader.peek()){
            case BEGIN_OBJECT:
                JSONObject object=new JSONObject();Set<String> names=new HashSet<>();reader.beginObject();while(reader.hasNext()){String name=reader.nextName();require(names.add(name),"导入清单含重复字段");object.put(name,read(reader,depth+1,items));}reader.endObject();return object;
            case BEGIN_ARRAY:
                JSONArray array=new JSONArray();reader.beginArray();while(reader.hasNext())array.put(read(reader,depth+1,items));reader.endArray();return array;
            case STRING:return reader.nextString();
            case BOOLEAN:return reader.nextBoolean();
            case NULL:reader.nextNull();return JSONObject.NULL;
            case NUMBER:String number=reader.nextString();require(number.matches("-?(0|[1-9][0-9]*)"),"清单数值无效");return Long.parseLong(number);
            default:throw new IOException("导入清单 JSON 无效");
        }
    }
    static void require(boolean condition,String message)throws IOException{if(!condition)throw new IOException(message);}
    static String string(JSONObject object,String key,int max)throws Exception{Object value=object.get(key);require(value instanceof String&&((String)value).length()<=max&&!((String)value).contains("\u0000")&&StandardCharsets.UTF_8.newEncoder().canEncode((String)value),"字段无效："+key);return (String)value;}
    static String uuid(JSONObject object,String key)throws Exception{String id=string(object,key,36);require(UUID.fromString(id).toString().equals(id),"编号无效");return id;}
    static void flag(JSONObject object,String key)throws Exception{Object value=object.get(key);require((value instanceof Integer||value instanceof Long)&&(((Number)value).longValue()==0||((Number)value).longValue()==1),"状态无效："+key);}
    static List<String> labels(JSONArray array,int count,int length)throws Exception{
        require(array.length()<=count,"标签数量过多");List<String> result=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(int i=0;i<array.length();i++){Object value=array.get(i);require(value instanceof String,"标签无效");String name=(String)value;require(!name.isEmpty()&&name.equals(name.trim())&&name.length()<=length&&!name.contains("\u0000")&&seen.add(name),"标签无效或重复");result.add(name);}return result;
    }
    static void validate(JSONObject record,int version)throws Exception{
        Set<String> allowed=new HashSet<>(Arrays.asList("id","title","diary_date","body_html","created_at","updated_at","pinned","outside_timeline","categories","tags","temporary_tags","people","assets"));for(Iterator<String> keys=record.keys();keys.hasNext();)require(allowed.contains(keys.next()),"文章字段不受支持，请更新软件");
        uuid(record,"id");require(!string(record,"title",10000).trim().isEmpty(),"文章标题为空");
        String date=string(record,"diary_date",32);require(date.matches("[0-9]{4}-([0-9]{2}|未知)-([0-9]{2}|未知)")&&PartialDate.normalize(date).equals(date)&&Integer.parseInt(date.substring(0,4))>=1753,"文章日期无效");
        string(record,"body_html",2*1024*1024);timestamp(string(record,"created_at",64));timestamp(string(record,"updated_at",64));flag(record,"pinned");
        if(record.has("outside_timeline"))require(record.get("outside_timeline") instanceof Boolean,"时间线状态无效");
        for(String kind:new String[]{"categories","tags","temporary_tags"})labels(record.getJSONArray(kind),500,1000);
        if(version>=2)require(record.has("people"),"人物清单缺失");
        JSONArray people=record.optJSONArray("people");if(record.has("people"))require(people!=null,"人物清单无效");
        if(people!=null){require(people.length()<=500,"人物过多");Set<String> ids=new HashSet<>(),codes=new HashSet<>();for(int i=0;i<people.length();i++){JSONObject p=people.getJSONObject(i);validatePerson(p);require(ids.add(p.getString("id"))&&codes.add(p.getString("code")),"人物或代号重复");}}
        JSONArray assets=record.getJSONArray("assets");require(assets.length()<=1000,"附件过多");Set<String> ids=new HashSet<>(),paths=new HashSet<>();
        for(int i=0;i<assets.length();i++){JSONObject asset=assets.getJSONObject(i);String id=uuid(asset,"id"),path=string(asset,"relative_path",200);require(ids.add(id)&&paths.add(path),"附件记录重复");require(path.matches("attachments/[A-Za-z0-9_-]+\\.[A-Za-z0-9]+"),"附件路径无效");require(string(asset,"archive_path",200).matches("EPUB/images/image-[1-9][0-9]*\\.(png|jpg|gif)"),"书内图片路径无效");require(Arrays.asList("image/png","image/jpeg","image/gif").contains(string(asset,"media_type",40)),"图片格式无效");require(string(asset,"sha256",64).matches("[0-9a-f]{64}"),"图片摘要无效");string(asset,"name",1000);string(asset,"caption",10000);}
    }
    private static void timestamp(String value)throws IOException{try{try{OffsetDateTime.parse(value.replace(' ','T'));}catch(RuntimeException e){LocalDateTime.parse(value.replace(' ','T'));}}catch(RuntimeException e){throw new IOException("文章时间无效",e);}}
    static void validatePerson(JSONObject p)throws Exception{
        uuid(p,"id");for(String key:new String[]{"name","code"}){String value=string(p,key,100);require(!value.isEmpty()&&value.equals(value.trim()),"人物姓名或代号无效");}
        for(String key:new String[]{"birth_date","met_date"}){String value=string(p,key,32);if(!value.isEmpty())PartialDate.normalize(value);}
        string(p,"met_how",10000);flag(p,"pinned");flag(p,"starred");for(String key:new String[]{"relationships","temporary_relationships"})if(p.has(key))labels(p.getJSONArray(key),100,100);
        Set<String> allowed=new HashSet<>(Arrays.asList("id","name","code","birth_date","met_date","met_how","pinned","starred","relationships","temporary_relationships"));for(Iterator<String> keys=p.keys();keys.hasNext();)require(allowed.contains(keys.next()),"人物字段不受支持");
    }
    static JSONObject article(DiaryStore store,String id,JSONArray assets)throws Exception{
        JSONObject record=row(store,"SELECT * FROM articles WHERE id=?",id);for(String key:new String[]{"deleted_at","sort_order","body_text"})record.remove(key);
        record.put("outside_timeline",!store.strings("SELECT article_id FROM outside_articles WHERE article_id=?",id).isEmpty());
        record.put("categories",new JSONArray(store.get(id).categories)).put("tags",new JSONArray(store.get(id).tags)).put("temporary_tags",new JSONArray(store.strings("SELECT name FROM article_temporary_tags WHERE article_id=? ORDER BY name",id)));
        JSONArray people=new JSONArray();for(String person:store.strings("SELECT person_id FROM article_people WHERE article_id=? ORDER BY person_id",id))people.put(person(store,person));record.put("people",people);
        List<JSONObject> sorted=new ArrayList<>();for(int i=0;i<assets.length();i++)sorted.add(assets.getJSONObject(i));sorted.sort(Comparator.comparing(a->a.optString("relative_path")));JSONArray ordered=new JSONArray();for(JSONObject a:sorted)ordered.put(a);record.put("assets",ordered);return record;
    }
    static JSONObject person(DiaryStore store,String id)throws Exception{
        JSONObject p=row(store,"SELECT * FROM people WHERE id=?",id);
        List<String> normal=store.strings("SELECT name FROM person_relationship_tags WHERE person_id=? ORDER BY name",id),temporary=store.strings("SELECT name FROM person_temporary_relationship_tags WHERE person_id=? ORDER BY name",id);
        if(!normal.isEmpty())p.put("relationships",new JSONArray(normal));if(!temporary.isEmpty())p.put("temporary_relationships",new JSONArray(temporary));return p;
    }
    private static JSONObject row(DiaryStore store,String sql,String id)throws Exception{
        try(Cursor c=store.getReadableDatabase().rawQuery(sql,new String[]{id})){require(c.moveToFirst(),"记录不存在");JSONObject object=new JSONObject();for(int i=0;i<c.getColumnCount();i++)object.put(c.getColumnName(i),c.getType(i)==Cursor.FIELD_TYPE_INTEGER?c.getLong(i):c.isNull(i)?JSONObject.NULL:c.getString(i));return object;}
    }
    static String fingerprint(JSONObject record)throws Exception{
        JSONObject data=new JSONObject(record.toString());if(!data.optBoolean("outside_timeline",false))data.remove("outside_timeline");
        JSONArray people=data.optJSONArray("people");if(people==null||people.length()==0)data.remove("people");else{List<JSONObject> list=new ArrayList<>();for(int i=0;i<people.length();i++)list.add(people.getJSONObject(i));list.sort(Comparator.comparing(p->p.optString("id")));JSONArray sorted=new JSONArray();for(JSONObject p:list)sorted.put(p);data.put("people",sorted);}
        JSONArray assets=data.getJSONArray("assets");for(int i=0;i<assets.length();i++)assets.getJSONObject(i).remove("archive_path");return sha256(canonical(data,false).getBytes(StandardCharsets.UTF_8));
    }
    static String sha256(byte[] bytes)throws Exception{return hex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    static String sha256(File file)throws Exception{MessageDigest digest=MessageDigest.getInstance("SHA-256");try(InputStream in=new FileInputStream(file)){byte[] bytes=new byte[8192];int n;while((n=in.read(bytes))!=-1)digest.update(bytes,0,n);}return hex(digest.digest());}
    private static String hex(byte[] bytes){StringBuilder out=new StringBuilder();for(byte b:bytes)out.append(String.format(Locale.ROOT,"%02x",b&255));return out.toString();}
    static String stableId(String name)throws Exception{
        UUID namespace=UUID.fromString("6ba7b811-9dad-11d1-80b4-00c04fd430c8");java.nio.ByteBuffer buffer=java.nio.ByteBuffer.allocate(16);buffer.putLong(namespace.getMostSignificantBits()).putLong(namespace.getLeastSignificantBits());MessageDigest hash=MessageDigest.getInstance("SHA-1");hash.update(buffer.array());byte[] data=hash.digest(name.getBytes(StandardCharsets.UTF_8));data[6]=(byte)((data[6]&15)|80);data[8]=(byte)((data[8]&63)|128);java.nio.ByteBuffer uuid=java.nio.ByteBuffer.wrap(data);return new UUID(uuid.getLong(),uuid.getLong()).toString();
    }
    static String canonical(Object value,boolean spaced)throws Exception{
        if(value instanceof JSONObject){JSONObject object=(JSONObject)value;List<String> keys=new ArrayList<>();for(Iterator<String> i=object.keys();i.hasNext();)keys.add(i.next());Collections.sort(keys);List<String> parts=new ArrayList<>();for(String key:keys)parts.add(quote(key)+(spaced?": ":":")+canonical(object.get(key),spaced));return "{"+String.join(spaced?", ":",",parts)+"}";}
        if(value instanceof JSONArray){JSONArray array=(JSONArray)value;List<String> parts=new ArrayList<>();for(int i=0;i<array.length();i++)parts.add(canonical(array.get(i),spaced));return "["+String.join(spaced?", ":",",parts)+"]";}
        if(value instanceof String)return quote((String)value);if(value==JSONObject.NULL||value==null)return "null";if(value instanceof Boolean||value instanceof Integer||value instanceof Long)return value.toString();throw new IOException("清单数值无效");
    }
    private static String quote(String value){StringBuilder out=new StringBuilder("\"");for(int i=0;i<value.length();i++){char c=value.charAt(i);switch(c){case '"':out.append("\\\"");break;case '\\':out.append("\\\\");break;case '\n':out.append("\\n");break;case '\r':out.append("\\r");break;case '\t':out.append("\\t");break;case '\b':out.append("\\b");break;case '\f':out.append("\\f");break;default:if(c<32)out.append(String.format(Locale.ROOT,"\\u%04x",(int)c));else out.append(c);}}return out.append('"').toString();}
    private ExchangeRecords(){}
}

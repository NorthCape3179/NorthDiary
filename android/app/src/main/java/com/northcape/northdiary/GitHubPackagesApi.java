package com.northcape.northdiary;

import android.util.Base64;
import android.util.Base64OutputStream;
import org.json.*;
import javax.net.ssl.HttpsURLConnection;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.zip.*;

/** Desktop-compatible private EPUB packages. Never transfers or replaces a SQLite database. */
final class GitHubPackagesApi {
    static final long MAX_PACKAGE=20L*1024*1024;
    static final String MARKER="northdiary-data.json",NAME="[0-9]{8}T[0-9]{12}Z-[0-9a-f]{32}\\.epub";
    static final class Failure extends IOException {final int status;Failure(String message,int status){super(message);this.status=status;}}
    static final class Response {final int status;final byte[] body;Response(int status,byte[] body){this.status=status;this.body=body;}Response(int status,String body){this(status,body.getBytes(StandardCharsets.UTF_8));}}
    interface Transport {Response request(String method,String path,String token,JSONObject body,File upload,boolean raw,File destination,long limit)throws Exception;}
    static final class Repository {final String name,branch;final boolean writable;Repository(String name,String branch,boolean writable){this.name=name;this.branch=branch;this.writable=writable;}}
    static final class Package {final String name,path,sha,commit;final long size;Package(String name,String path,String sha,long size,String commit){this.name=name;this.path=path;this.sha=sha;this.size=size;this.commit=commit;}}
    private final String token;private final File cache;private final Transport transport;
    GitHubPackagesApi(File cache,String token){this(cache,token,new Network());}
    GitHubPackagesApi(File cache,String token,Transport transport){this.cache=cache;this.token=token;this.transport=transport;}
    static String repositoryName(String value)throws IOException{
        if(!value.matches("[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}"))throw new IOException("仓库请填写为 账号/仓库名");
        String name=value.substring(value.indexOf('/')+1);if(name.equals(".")||name.equals("..")||name.equalsIgnoreCase("NorthDiary"))throw new IOException("请使用独立私有数据仓库，例如 NorthDiary-Data，不能选择源码仓库");return value;
    }
    private static String encode(String value)throws Exception{return URLEncoder.encode(value,"UTF-8").replace("+","%20");}
    private Response call(String method,String path,JSONObject body,File upload,boolean raw,File destination,long limit)throws Exception{
        if(token.isEmpty()||token.length()>10000||token.chars().anyMatch(c->c<33||c==127))throw new IOException("请先登录 GitHub，并允许私有数据仓库读写权限");
        Response response=transport.request(method,path,token,body,upload,raw,destination,limit);
        if(response.status<200||response.status>=300){int status=response.status;String message;
            switch(status){case 401:message="GitHub 登录已失效，请重新登录";break;case 403:message="GitHub 拒绝访问，请检查私有仓库权限或稍后重试";break;case 404:message="仓库或文件不存在，或当前登录没有该私有仓库的权限";break;case 409:case 422:message="远端记录发生变化，请刷新远端列表后重试";break;case 429:message="GitHub 请求过于频繁，请稍后重试";break;default:message="GitHub 请求失败（HTTP "+status+"）";}
            throw new Failure(message,status);
        }return response;
    }
    private JSONObject object(String method,String path,JSONObject body)throws Exception{
        try{return new JSONObject(new String(call(method,path,body,null,false,null,2*1024*1024).body,StandardCharsets.UTF_8));}catch(JSONException e){throw new IOException("GitHub 返回的数据格式无效，请重试");}
    }
    private Repository metadata(String name)throws Exception{
        repositoryName(name);JSONObject json=object("GET","/repos/"+name,null);
        if(json.opt("private")!=Boolean.TRUE)throw new IOException("只允许连接 Private 私有数据仓库，请先检查仓库可见性");
        if(!json.optString("full_name").equalsIgnoreCase(name))throw new IOException("仓库名称不一致，请使用当前完整仓库名");
        String branch=json.optString("default_branch");if(branch.isEmpty()||branch.length()>255||branch.chars().anyMatch(c->c<32||c==127))throw new IOException("仓库默认分支无效");
        JSONObject permissions=json.optJSONObject("permissions");return new Repository(name,branch,permissions==null||permissions.optBoolean("push",false));
    }
    private String contents(String name,String path,String ref)throws Exception{return "/repos/"+name+"/contents/"+path+(ref==null?"":"?ref="+encode(ref));}
    private void marker(Repository repo)throws Exception{
        Response response=call("GET",contents(repo.name,MARKER,repo.branch),null,null,true,null,4096);JSONObject json;
        try{json=ExchangeRecords.parse(new String(response.body,StandardCharsets.UTF_8));}catch(Exception e){throw new IOException("数据仓库标识损坏，未读取或写入文章包");}
        Object version=json.opt("version");if(json.length()!=2||!json.optString("format").equals("NorthDiaryData")||!(version instanceof Integer||version instanceof Long)||((Number)version).longValue()!=1)throw new IOException("这不是受支持的 NorthDiary 数据仓库，请连接或初始化空的私有数据仓库");
    }
    Repository checkRepository(String name)throws Exception{Repository repo=metadata(name);marker(repo);return repo;}
    Repository initializeRepository(String name)throws Exception{
        Repository repo=metadata(name);if(!repo.writable)throw new IOException("当前登录没有仓库写入权限");
        try{marker(repo);return repo;}catch(Failure e){if(e.status!=404)throw e;}
        JSONArray rows;
        try{rows=new JSONArray(new String(call("GET",contents(name,"",null),null,null,false,null,2*1024*1024).body,StandardCharsets.UTF_8));}catch(Failure e){if(e.status!=404)throw e;rows=new JSONArray();}
        if(rows.length()!=0)throw new IOException("仓库已有其他文件，不能初始化；请使用空的私有数据仓库");
        JSONObject body=new JSONObject().put("message","Initialize NorthDiary data repository").put("content",Base64.encodeToString("{\"format\":\"NorthDiaryData\",\"version\":1}".getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP));
        object("PUT",contents(name,MARKER,null),body);return checkRepository(name);
    }
    List<Package> list(String name)throws Exception{
        Repository repo=checkRepository(name);String head=object("GET","/repos/"+name+"/branches/"+encode(repo.branch),null).getJSONObject("commit").getString("sha");if(!head.matches("[0-9a-f]{40}"))throw new IOException("仓库分支版本无效");
        JSONArray rows;try{rows=new JSONArray(new String(call("GET",contents(name,"packs",head),null,null,false,null,2*1024*1024).body,StandardCharsets.UTF_8));}catch(Failure e){if(e.status==404)return new ArrayList<>();throw e;}
        if(rows.length()>=1000)throw new IOException("远端文集过多，请使用新的私有数据仓库归档");List<Package> packages=new ArrayList<>();
        for(int i=0;i<rows.length();i++){JSONObject row=rows.getJSONObject(i);String filename=row.optString("name");if(!row.optString("type").equals("file")||!filename.matches(NAME))continue;
            Object size=row.opt("size");Package pack=new Package(filename,row.optString("path"),row.optString("sha"),size instanceof Number?((Number)size).longValue():-1,head);validate(pack);packages.add(pack);
        }packages.sort((a,b)->b.name.compareTo(a.name));return packages;
    }
    private static void validate(Package pack)throws IOException{if(!pack.name.matches(NAME)||!pack.path.equals("packs/"+pack.name)||!pack.sha.matches("[0-9a-f]{40}")||!pack.commit.matches("[0-9a-f]{40}")||pack.size<=0||pack.size>MAX_PACKAGE)throw new IOException("远端文集信息无效或超过 20 MiB，请刷新列表");}
    String upload(String name,File file)throws Exception{
        checkPackage(file);Repository repo=checkRepository(name);if(!repo.writable)throw new IOException("当前登录没有私有仓库写入权限，请重新授权或使用 Contents 读写令牌");
        String stamp=DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmssSSSSSS'Z'",Locale.ROOT).format(ZonedDateTime.now(ZoneOffset.UTC));String filename=stamp+"-"+UUID.randomUUID().toString().replace("-","")+".epub";
        JSONObject body=new JSONObject().put("message","Upload NorthDiary article package").put("branch",repo.branch);
        Response response=call("PUT",contents(name,"packs/"+filename,null),body,file,false,null,2*1024*1024);
        JSONObject result=new JSONObject(new String(response.body,StandardCharsets.UTF_8));if(!blobSha(file).equals(result.optJSONObject("content")==null?"":result.getJSONObject("content").optString("sha")))throw new IOException("上传结果未能核对，请先刷新远端列表确认结果，避免重复上传");return filename;
    }
    File download(String name,Package pack)throws Exception{
        checkRepository(name);validate(pack);File file=File.createTempFile("github-package-",".epub",cache);
        try{call("GET",contents(name,pack.path,pack.commit),null,null,true,file,MAX_PACKAGE);if(file.length()!=pack.size||!blobSha(file).equals(pack.sha))throw new IOException("下载大小或摘要不符，未导入本机文章");checkPackage(file);return file;}catch(Exception e){file.delete();throw e;}
    }
    static String blobSha(File file)throws Exception{
        MessageDigest hash=MessageDigest.getInstance("SHA-1");hash.update(("blob "+file.length()+"\u0000").getBytes(StandardCharsets.UTF_8));try(InputStream in=new FileInputStream(file)){byte[] data=new byte[8192];int n;while((n=in.read(data))!=-1)hash.update(data,0,n);}StringBuilder out=new StringBuilder();for(byte b:hash.digest())out.append(String.format(Locale.ROOT,"%02x",b&255));return out.toString();
    }
    static void checkPackage(File file)throws Exception{
        if(file.length()<=0||file.length()>MAX_PACKAGE)throw new IOException("GitHub 单本文集最多 20 MiB，请减少文章或图片后分批上传");
        try(ZipFile zip=new ZipFile(file)){
            if(zip.size()>5000)throw new IOException("文集文件过多");long total=0;Set<String> names=new HashSet<>();
            for(Enumeration<? extends ZipEntry> all=zip.entries();all.hasMoreElements();){ZipEntry e=all.nextElement();String name=e.getName();if(!names.add(name)||name.startsWith("/")||name.contains("\\")||name.contains(":")||Arrays.asList(name.split("/")).contains("..")||e.getSize()<0||e.getSize()>32L*1024*1024)throw new IOException("文集结构无效");total+=e.getSize();if(total>200L*1024*1024)throw new IOException("文集解压后过大");}
            ZipEntry mime=zip.getEntry("mimetype"),manifest=zip.getEntry(ExchangeRecords.PATH);if(mime==null||mime.getSize()!=20||manifest==null||manifest.getSize()>8*1024*1024)throw new IOException("仅允许传输 NorthDiary 原生 EPUB 文集");
            try(InputStream in=zip.getInputStream(mime)){if(!new String(DiaryStore.readBytes(in,64),StandardCharsets.UTF_8).equals("application/epub+zip"))throw new IOException("文集格式无效");}
            JSONObject data;try(InputStream in=zip.getInputStream(manifest)){data=ExchangeRecords.parse(new String(DiaryStore.readBytes(in,8*1024*1024),StandardCharsets.UTF_8));}
            Object version=data.opt("version");if(!data.optString("format").equals(ExchangeRecords.FORMAT)||!(version instanceof Integer||version instanceof Long)||((Number)version).longValue()<1||((Number)version).longValue()>4)throw new IOException("文集版本不受支持");
        }
    }
    static void writeUploadBody(OutputStream out,JSONObject body,File upload)throws Exception{
        String prefix="{\"message\":"+JSONObject.quote(body.getString("message"))+",\"branch\":"+JSONObject.quote(body.getString("branch"))+",\"content\":\"";out.write(prefix.getBytes(StandardCharsets.UTF_8));
        OutputStream keepOpen=new FilterOutputStream(out){@Override public void close()throws IOException{flush();}@Override public void write(byte[] b,int off,int len)throws IOException{out.write(b,off,len);}};
        try(InputStream in=new FileInputStream(upload);Base64OutputStream encoded=new Base64OutputStream(keepOpen,Base64.NO_WRAP)){DiaryStore.copy(in,encoded,MAX_PACKAGE);}out.write("\"}".getBytes(StandardCharsets.UTF_8));
    }
    static final class Network implements Transport {
        public Response request(String method,String path,String token,JSONObject body,File upload,boolean raw,File destination,long limit)throws Exception{
            if(!path.startsWith("/")||path.startsWith("//")||path.contains("\r")||path.contains("\n"))throw new IOException("GitHub 请求地址无效");
            HttpsURLConnection connection=(HttpsURLConnection)new URL("https://api.github.com"+path).openConnection();connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(20000);connection.setReadTimeout(30000);connection.setRequestMethod(method);
            connection.setRequestProperty("Authorization","Bearer "+token);connection.setRequestProperty("Accept",raw?"application/vnd.github.raw+json":"application/vnd.github+json");connection.setRequestProperty("User-Agent","NorthDiary-Android");connection.setRequestProperty("X-GitHub-Api-Version","2022-11-28");
            try{
                if(body!=null){connection.setDoOutput(true);connection.setRequestProperty("Content-Type","application/json");if(upload!=null)connection.setChunkedStreamingMode(65536);
                    try(OutputStream out=connection.getOutputStream()){
                        if(upload==null)out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                        else writeUploadBody(out,body,upload);
                    }
                }
                int status=connection.getResponseCode();if(status<200||status>=300)return new Response(status,new byte[0]);
                try(InputStream in=connection.getInputStream()){
                    if(destination==null)return new Response(status,DiaryStore.readBytes(in,limit));
                    try(OutputStream out=new FileOutputStream(destination)){DiaryStore.copy(in,out,limit);}return new Response(status,new byte[0]);
                }
            }catch(IOException e){throw new IOException("无法完成 GitHub 连接。上传时若连接中断，请先刷新远端列表确认结果再重试");}finally{connection.disconnect();}
        }
    }
}

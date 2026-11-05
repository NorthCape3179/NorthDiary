package com.northcape.northdiary;

import org.json.*;
import javax.net.ssl.HttpsURLConnection;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Explicit account-only or private-repository device authorization. */
final class GitHubAuthApi {
    static final String DEVICE="https://github.com/login/device/code",TOKEN="https://github.com/login/oauth/access_token",USER="https://api.github.com/user";
    interface Transport {JSONObject request(String url,String token,Map<String,String> form)throws Exception;}
    static final class Challenge {
        final String userCode,deviceCode;final int interval,expires;final boolean repositoryAccess;
        Challenge(String userCode,String deviceCode,int interval,int expires){this(userCode,deviceCode,interval,expires,false);}
        Challenge(String userCode,String deviceCode,int interval,int expires,boolean repositoryAccess){this.userCode=userCode;this.deviceCode=deviceCode;this.interval=interval;this.expires=expires;this.repositoryAccess=repositoryAccess;}
    }
    static final class Poll {
        final String state,token;
        Poll(String state,String token){this.state=state;this.token=token;}
    }
    private final Transport transport;
    GitHubAuthApi(){this(new Network());}
    GitHubAuthApi(Transport transport){this.transport=transport;}
    Challenge start(String client)throws Exception {
        return start(client,false);
    }
    Challenge start(String client,boolean repositoryAccess)throws Exception {
        if(!client.matches("[A-Za-z0-9_.-]{1,100}"))throw new IOException("请填写桌面端使用的 OAuth Client ID，并确认该应用已启用设备授权。");
        Map<String,String> form=new LinkedHashMap<>();form.put("client_id",client);form.put("scope",repositoryAccess?"read:user repo":"read:user");
        JSONObject j=transport.request(DEVICE,"",form);
        if(j.has("error"))throw new IOException("无法开始授权，请确认 Client ID 正确且已启用设备授权。");
        String user=j.optString("user_code"),device=j.optString("device_code");int interval=j.optInt("interval",5),expires=j.optInt("expires_in");
        if(!"https://github.com/login/device".equals(j.optString("verification_uri"))||!user.matches("[A-Z0-9-]{4,32}")||device.isEmpty()||device.length()>1024||interval<5||interval>60||expires<1||expires>1800)
            throw new IOException("GitHub 授权响应无效，请重试。");
        return new Challenge(user,device,interval,expires,repositoryAccess);
    }
    Poll poll(String client,Challenge challenge)throws Exception {
        Map<String,String> form=new LinkedHashMap<>();form.put("client_id",client);form.put("device_code",challenge.deviceCode);form.put("grant_type","urn:ietf:params:oauth:grant-type:device_code");
        JSONObject j=transport.request(TOKEN,"",form);String error=j.optString("error","");
        if(error.equals("authorization_pending")||error.equals("slow_down"))return new Poll(error,"");
        if(!error.isEmpty())throw new IOException(error.equals("access_denied")?"已取消 GitHub 授权。":error.equals("expired_token")?"验证码已过期，请重新登录。":"GitHub 授权未完成，请重新开始。");
        String token=j.optString("access_token","");if(token.isEmpty()||token.length()>10000||!j.optString("token_type").equalsIgnoreCase("bearer"))throw new IOException("GitHub 未返回有效的访问凭据。");
        if(challenge.repositoryAccess&&!Arrays.asList(j.optString("scope").split("[, ]+")).contains("repo"))throw new IOException("此次授权缺少私有仓库权限，请重新授权或使用有 Contents 读写权限的专用令牌");
        return new Poll("connected",token);
    }
    String user(String token)throws Exception {
        if(token.isEmpty()||token.length()>10000||token.contains("\n")||token.contains("\r"))throw new IOException("访问令牌格式无效。");
        JSONObject j=transport.request(USER,token,null);String login=j.optString("login");
        if(!login.matches("[A-Za-z0-9-]{1,39}")||j.optLong("id")<=0)throw new IOException("GitHub 账号响应无效。");return login;
    }
    static final class Network implements Transport {
        public JSONObject request(String url,String token,Map<String,String> form)throws Exception {
            if(!url.equals(DEVICE)&&!url.equals(TOKEN)&&!url.equals(USER))throw new IOException("请求地址不受支持。");
            HttpsURLConnection connection=(HttpsURLConnection)new URL(url).openConnection();
            connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(20000);connection.setReadTimeout(20000);
            connection.setRequestProperty("Accept","application/json");connection.setRequestProperty("User-Agent","NorthDiary-Android");connection.setRequestProperty("X-GitHub-Api-Version","2022-11-28");
            if(!token.isEmpty()){if(!url.equals(USER))throw new IOException("不允许向授权端点发送已有令牌。");connection.setRequestProperty("Authorization","Bearer "+token);}
            try {
                if(form!=null){
                    connection.setRequestMethod("POST");connection.setDoOutput(true);connection.setRequestProperty("Content-Type","application/x-www-form-urlencoded");StringJoiner body=new StringJoiner("&");
                    for(Map.Entry<String,String> pair:form.entrySet())body.add(URLEncoder.encode(pair.getKey(),"UTF-8")+"="+URLEncoder.encode(pair.getValue(),"UTF-8"));
                    try(OutputStream out=connection.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}
                }
                int code=connection.getResponseCode();if(code<200||code>=300)throw new IOException(code==401?"GitHub 登录已失效，请重新授权。":"GitHub 连接失败（HTTP "+code+"），请检查网络后重试。");
                try(InputStream in=connection.getInputStream()){return new JSONObject(new String(DiaryStore.readBytes(in,1024*1024),StandardCharsets.UTF_8));}
            }finally{connection.disconnect();}
        }
    }
}

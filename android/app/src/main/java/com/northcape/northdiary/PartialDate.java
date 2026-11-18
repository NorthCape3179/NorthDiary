package com.northcape.northdiary;

import java.time.LocalDate;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Uses the desktop's YYYY-未知-未知 representation without fabricating dates. */
public final class PartialDate {
    private static final Pattern FORMAT = Pattern.compile("([0-9]{4})(?:-([0-9]{2}|未知)(?:-([0-9]{2}|未知))?)?");
    private PartialDate() { }
    public static String normalize(String input) {
        Matcher m = FORMAT.matcher(input.trim());
        if (!m.matches()) throw new IllegalArgumentException("日期请填写 YYYY、YYYY-MM 或 YYYY-MM-DD");
        int y = Integer.parseInt(m.group(1));
        String month = m.group(2), day = m.group(3);
        boolean noMonth = month == null || month.equals("未知");
        boolean noDay = day == null || day.equals("未知");
        if (y < 1 || noMonth && !noDay) throw new IllegalArgumentException("月份未知时不能指定日子");
        try { LocalDate.of(y, noMonth ? 1 : Integer.parseInt(month), noDay ? 1 : Integer.parseInt(day)); }
        catch (RuntimeException e) { throw new IllegalArgumentException("日期不存在"); }
        return m.group(1) + "-" + (noMonth ? "未知" : month) + "-" + (noDay ? "未知" : day);
    }
    public static String label(String date) {
        String d = normalize(date);
        String[] p = d.split("-");
        return p[0] + "年" + (p[1].equals("未知") ? "" : Integer.parseInt(p[1]) + "月")
            + (p[2].equals("未知") ? "" : Integer.parseInt(p[2]) + "日");
    }
}

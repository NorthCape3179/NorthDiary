package com.northcape.northdiary;

import java.util.ArrayList;
import java.util.List;

final class Models {
    static final class Article {
        String id, title = "", date = java.time.LocalDate.now().toString();
        String html = "", text = "", created = "", updated = "";
        boolean outside, draft, deleted;
        List<String> tags = new ArrayList<>(), people = new ArrayList<>();
        // Null means an older edit journal/caller did not edit categories.
        List<String> categories;
    }
    static final class Person {
        String id, name = "", code = "", birth = "", met = "", how = "";
    }
    static final class Attachment {
        String id, name, path, mime;
    }
}

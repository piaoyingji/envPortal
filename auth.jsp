<%@ page language="java" contentType="text/plain; charset=UTF-8" pageEncoding="UTF-8" trimDirectiveWhitespaces="true" %>
<%
    request.setCharacterEncoding("UTF-8");
    String pwd = request.getParameter("pwd");
    if ("nho1234567".equals(pwd)) {
        out.print("OK");
    } else {
        out.print("NG");
    }
%>

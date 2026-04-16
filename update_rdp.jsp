<%@ page language="java" contentType="text/plain; charset=UTF-8" pageEncoding="UTF-8" trimDirectiveWhitespaces="true" %>
<%@ page import="java.io.*" %>
<%
    // 设置请求和响应的编码
    request.setCharacterEncoding("UTF-8");
    response.setCharacterEncoding("UTF-8");

    try {
        // 1. 读取前端以 POST 方式发过来的 CSV 原文
        StringBuilder sb = new StringBuilder();
        BufferedReader reader = request.getReader();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line).append("\n");
        }
        String csvData = sb.toString();

        if (csvData != null && !csvData.trim().isEmpty()) {
            // 2. 获取当前项目根目录下 rdp.csv 的绝对路径
            String filePath = getServletContext().getRealPath("/rdp.csv");
            if (filePath == null) {
                filePath = getServletContext().getRealPath("/") + "rdp.csv";
            }
            File file = new File(filePath);
            
            // 3. 写入文件（带 UTF-8 BOM 以兼容 Excel 查看）
            FileOutputStream fos = new FileOutputStream(file);
            fos.write(0xEF);
            fos.write(0xBB);
            fos.write(0xBF);
            fos.write(csvData.getBytes("UTF-8"));
            fos.close();
            
            out.print("success");
        } else {
            response.setStatus(400);
            out.print("No data received");
        }
    } catch (Exception e) {
        response.setStatus(500);
        out.print("Server Error: " + e.getMessage());
    }
%>

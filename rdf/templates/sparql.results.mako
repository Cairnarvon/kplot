<html>
<head>
    <title>SPARQL endpoint</title>
</head>
<body>
<table>
    <tr>
        <th>Subject</th>
        <th>Predicate</th>
        <th>Object</th>
    </tr>
% for triple in result:
    <tr>
        <td class="subject">${triple[0]}</td>
        <td class="predicate">${triple[2]}</td>
        <td class="object">${triple[1]}</td>
    </tr>
% endfor
</table>
</body>
</html>

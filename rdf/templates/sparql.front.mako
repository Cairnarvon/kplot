<html>
<head>
<title>SPARQL endpoint</title>
</head>
<body>
<form action='/sparql' method='post'>
    <textarea name="query" cols="80" rows="26">PREFIX our: &lt;${ontology}&gt;
SELECT *
WHERE {
    ?a ?b ?c.
}</textarea>
    <input type="hidden" name="type" value="html" />
    <br />
    <input type="submit" value="Submit" />
</form>
</body>
</html>

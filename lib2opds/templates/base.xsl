<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
  <xsl:output method="html" indent="yes" encoding="UTF-8"/>
  <xsl:template match="/">
  <html>
    <head>
      <meta charset="utf-8" />
      <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'" />
      <link rel="stylesheet" type="text/css" href="{{ config.get_assets_uri() }}/style.css" />
      <title><xsl:value-of select="/atom:feed/atom:title"/></title>
    </head>
    <body>
    <div id="header">
    <xsl:apply-templates select="/atom:feed/atom:link[@rel='start']" />
    <xsl:apply-templates select="/atom:feed/atom:link[@rel='up']" />
    <xsl:value-of select="/atom:feed/atom:title"/>
    </div>
      <div id="content">
      {% block content %}{% endblock %}
      </div>
      <div id="footer">&#8635; <xsl:value-of select="translate(/atom:feed/atom:updated, 'T', ' ')"/></div>
    </body>
  </html>
  </xsl:template>
{% block templates %}{% endblock %}
  <xsl:template match="/atom:feed/atom:link[@rel='start']">
    <xsl:element name="a">
      <xsl:attribute name="href">
      <xsl:value-of select="./@href"/>
      </xsl:attribute>{{ config.library_title }}</xsl:element><xsl:text> </xsl:text>
  </xsl:template>
  <xsl:template match="/atom:feed/atom:link[@rel='up']">
    <xsl:element name="a">
      <xsl:attribute name="href">
      <xsl:value-of select="./@href"/>
      </xsl:attribute>/../</xsl:element><xsl:text> </xsl:text>
  </xsl:template>
</xsl:stylesheet>

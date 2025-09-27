{% extends "base.xsl" %}
{% block content %}
        <h1><xsl:value-of select="/atom:feed/atom:title"/></h1>
        <table>
          <xsl:apply-templates select="/atom:feed/atom:entry" />
        </table>
{% endblock %}
{% block templates %}
  <xsl:template match="atom:entry">
    <tr><td><xsl:apply-templates select="atom:link[@rel='http://opds-spec.org/image']" /></td>
    <td>
      <strong><xsl:value-of select="atom:title"/></strong><br />
      <xsl:apply-templates select="atom:author" />
    </td>
    <td><xsl:apply-templates select="atom:link[@rel='http://opds-spec.org/acquisition']" /></td>
    </tr>
  </xsl:template>
  <xsl:template match="atom:author">
    <xsl:value-of select="atom:name"/><xsl:if test="position() &lt; last()">, </xsl:if>
  </xsl:template>
  <xsl:template match="atom:link[@rel = 'http://opds-spec.org/acquisition']">
      <xsl:element name="a">
            <xsl:attribute name="href">
                <xsl:value-of select="./@href"/>
            </xsl:attribute>
            <xsl:choose>
              <xsl:when test="./@type = 'application/epub+zip'">EPUB</xsl:when>
              <xsl:when test="./@type = 'application/pdf'">PDF</xsl:when>
              <xsl:otherwise><xsl:value-of select="./@type"/></xsl:otherwise>
            </xsl:choose>
        </xsl:element><xsl:if test="position() &lt; last()">, </xsl:if>
  </xsl:template>
  <xsl:template match="atom:link[@rel='http://opds-spec.org/image']">
    <xsl:element name="img">
      <xsl:attribute name="src"><xsl:value-of select="./@href"/></xsl:attribute>
      <xsl:attribute name="class">cover</xsl:attribute>
    </xsl:element>
  </xsl:template>
{% endblock %}
</xsl:stylesheet>

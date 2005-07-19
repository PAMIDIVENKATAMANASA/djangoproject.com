<?xml version="1.0"?>
<!-- RSS generated by Trac v<?cs var:$trac.version ?> on <?cs var:$trac.time ?> -->
<rss version="2.0">
   <?cs set base_url = $HTTP.Protocol+'://'+$HTTP.Host ?>
   <?cs if $HTTP.Port ?>
     <?cs set base_url = $base_url + ':' + $HTTP.Port ?>
   <?cs /if ?>
    <channel>
      <?cs if $project.name.encoded ?>
        <title><?cs var:$project.name.encoded ?>: <?cs var:$report.title ?></title>

      <?cs else ?>
        <title><?cs var:$title ?></title>
      <?cs /if ?>
      <link><?cs var:$base_url ?><?cs var:$trac.href.report ?>/<?cs var:$report.id ?></link>
      <description>Trac Report - <?cs var:$report.title ?></description>
      <language>en-us</language>
      <generator>Trac v<?cs var:$trac.version ?></generator>
      <?cs each:row = $report.items ?>
        <?cs set title = '' ?>
        <?cs set descr = '' ?>
        <?cs set author = '' ?>
        <?cs set pubdate = '' ?>
        <?cs each:item = $row ?>
          <?cs if name(item) == 'ticket' ?>
            <?cs set link = $base_url+$item.ticket_href ?>
            <?cs set id = $item ?>
          <?cs elif name(item) == 'summary' ?>
            <?cs set title = $item ?>
          <?cs elif name(item) == 'description' ?>
            <?cs set descr = $item ?>
          <?cs elif name(item) == 'reporter' ?>
            <?cs set author = $item.rss ?>
          <?cs elif name(item) == 'time' || name(item) == 'changetime' 
                    || name(item) == 'created' || name(item) == 'modified' ?>
            <?cs set pubdate = $item.gmt ?>
          <?cs /if ?>
       <?cs /each ?>
       <item>
         <?cs if:$author ?>
          <author><?cs var:$author ?></author>
         <?cs /if ?>
         <pubDate><?cs var:$pubdate ?></pubDate>
         <title><?cs var:'#'+$id+': '+$title ?></title>   
         <link><?cs var:$link ?></link>
         <description><?cs var:$descr ?></description>
         <category>Report</category>
       </item>
      <?cs /each ?>
    </channel>
</rss>

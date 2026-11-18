<?php
// RedKyber · API de entrada: otro sistema envía registros en JSON y se insertan en una tabla.
// POST servicios/entrada.php  con la cabecera X-Clave-Api y el cuerpo {"tabla":"clientes","clave_unica":"email","registros":[{...}]}
// La clave está en la variable de entorno REDKYBER_CLAVE o en data/clave-integracion.txt (fuera de git).
// Solo se aceptan columnas que existan en la tabla; si se indica clave_unica, se omiten los registros ya existentes.
header('Content-Type: application/json; charset=utf-8');
define('RUTA_BD', getenv('REDKYBER_DB') ?: __DIR__.'/../data/redkyber.db');

function responder($codigo,$datos){ http_response_code($codigo); echo json_encode($datos,JSON_UNESCAPED_UNICODE); exit; }

$clave=getenv('REDKYBER_CLAVE') ?: (is_file(__DIR__.'/../data/clave-integracion.txt') ? trim(file_get_contents(__DIR__.'/../data/clave-integracion.txt')) : '');
if($clave==='') responder(503,['ok'=>false,'error'=>'La integración no está configurada (falta la clave)']);
if($_SERVER['REQUEST_METHOD']!=='POST') responder(405,['ok'=>false,'error'=>'Usa POST']);
if(!hash_equals($clave,$_SERVER['HTTP_X_CLAVE_API'] ?? '')) responder(401,['ok'=>false,'error'=>'Clave incorrecta']);

$e=json_decode(file_get_contents('php://input'),true);
if(!is_array($e) || empty($e['tabla']) || !is_array($e['registros'] ?? null)) responder(400,['ok'=>false,'error'=>'Formato no válido']);

$db=new SQLite3(RUTA_BD); $db->enableExceptions(true);
$tablas=[]; $r=$db->query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"); while($f=$r->fetchArray(SQLITE3_ASSOC)) $tablas[]=$f['name'];
if(!in_array($e['tabla'],$tablas,true)) responder(400,['ok'=>false,'error'=>'Tabla no válida']);
$q='"'.str_replace('"','""',$e['tabla']).'"';
$columnas=[]; $r=$db->query("PRAGMA table_info($q)"); while($f=$r->fetchArray(SQLITE3_ASSOC)) if(!$f['pk']) $columnas[]=$f['name'];
$unica=$e['clave_unica'] ?? null; if($unica!==null && !in_array($unica,$columnas,true)) responder(400,['ok'=>false,'error'=>'clave_unica no válida']);

$insertados=0; $omitidos=0;
$db->exec('BEGIN');
try{
  foreach($e['registros'] as $reg){
    $reg=array_intersect_key((array)$reg,array_flip($columnas));
    if(!$reg){ $omitidos++; continue; }
    if($unica!==null){
      if(($reg[$unica] ?? '')==='' ){ $omitidos++; continue; } // sin valor en la clave única no se puede comprobar si ya existe
      $s=$db->prepare("SELECT COUNT(*) FROM $q WHERE \"$unica\" = ?"); $s->bindValue(1,$reg[$unica] ?? null); 
      if($s->execute()->fetchArray()[0]>0){ $omitidos++; continue; }
    }
    $campos=array_keys($reg);
    $s=$db->prepare("INSERT INTO $q (".implode(',',array_map(fn($c)=>'"'.str_replace('"','""',$c).'"',$campos)).") VALUES (".implode(',',array_fill(0,count($campos),'?')).")");
    $i=1; foreach($reg as $v) $s->bindValue($i++,$v,SQLITE3_TEXT); $s->execute(); $insertados++;
  }
  $db->exec('COMMIT');
}catch(Throwable $x){ $db->exec('ROLLBACK'); responder(400,['ok'=>false,'error'=>$x->getMessage()]); }
responder(200,['ok'=>true,'insertados'=>$insertados,'omitidos'=>$omitidos]);

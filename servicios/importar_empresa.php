<?php
// RedKyber · Integración con otro sistema de gestión: la base «empresa.db» de la unidad 007-IA de clase
// (tabla clientes con nombre, apellidos, email y teléfono). Se lee en solo lectura y se envía a servicios/entrada.php.
// Uso: php servicios/importar_empresa.php <empresa.db> [URL_de_entrada]
// La clave se toma de REDKYBER_CLAVE o de data/clave-integracion.txt.
if($argc<2){ fwrite(STDERR,"Uso: php servicios/importar_empresa.php <base.sqlite> [url]\n"); exit(1); }
$url=$argv[2] ?? 'http://127.0.0.1:8000/servicios/entrada.php';
$clave=getenv('REDKYBER_CLAVE') ?: trim(@file_get_contents(__DIR__.'/../data/clave-integracion.txt'));
$origen=new SQLite3($argv[1],SQLITE3_OPEN_READONLY);
$registros=[]; $r=$origen->query('SELECT nombre, apellidos, email, telefono FROM clientes');
while($f=$r->fetchArray(SQLITE3_ASSOC)){
  // Campos del origen -> campos de RedKyber (el país no existe en el origen)
  $registros[]=['nombre'=>trim($f['nombre'].' '.$f['apellidos']),'email'=>$f['email'],'telefono'=>$f['telefono'],'pais'=>'Sin indicar'];
}
$cuerpo=json_encode(['tabla'=>'clientes','clave_unica'=>'email','registros'=>$registros],JSON_UNESCAPED_UNICODE);
$contexto=stream_context_create(['http'=>['method'=>'POST','header'=>"Content-Type: application/json\r\nX-Clave-Api: $clave\r\n",'content'=>$cuerpo,'ignore_errors'=>true]]);
echo count($registros)." clientes leídos del sistema de origen\n";
echo file_get_contents($url,false,$contexto),"\n";

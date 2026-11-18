<?php
// RedKyber · Pruebas de la API. Uso: php pruebas/pruebas.php
// Crea una base temporal a partir de data/schema.sql y data/demo.sql, arranca un servidor PHP propio
// en el puerto 8099 y comprueba las rutas por HTTP. No toca data/redkyber.db.
$raiz=dirname(__DIR__); $tmp=sys_get_temp_dir().'/redkyber_pruebas_'.getmypid(); mkdir($tmp);
$bd="$tmp/prueba.db"; $db=new SQLite3($bd); $db->exec(file_get_contents("$raiz/data/schema.sql")); $db->exec(file_get_contents("$raiz/data/demo.sql")); $db->close();
$clave='clave-de-prueba'; $puerto=8099; $base="http://127.0.0.1:$puerto";
$servidor=proc_open(['php','-S',"127.0.0.1:$puerto",'-t',$raiz],[1=>['file','/dev/null','w'],2=>['file','/dev/null','w']],$pipes,$raiz,['REDKYBER_DB'=>$bd,'REDKYBER_CLAVE'=>$clave,'PATH'=>getenv('PATH')]);
usleep(700000);

function llamar($url,$cuerpo=null,$cabeceras=[]){
  global $base;
  $c=['http'=>['method'=>$cuerpo===null?'GET':'POST','ignore_errors'=>true,'header'=>implode("\r\n",array_merge(['Content-Type: application/json'],$cabeceras))."\r\n",'content'=>$cuerpo===null?'':json_encode($cuerpo)]];
  $texto=file_get_contents($base.$url,false,stream_context_create($c));
  preg_match('/ (\d{3}) /',$http_response_header[0] ?? '',$m);
  return [(int)($m[1] ?? 0),json_decode($texto,true)];
}
$total=0; $fallos=0;
function prueba($nombre,$condicion){ global $total,$fallos; $total++; if(!$condicion) $fallos++; echo ($condicion?'  OK     ':'  FALLO  ').$nombre."\n"; }
$api='/api/superapi.php?ruta=';
$n=fn($tabla)=>count(llamar($api.'tabla&tabla='.$tabla)[1]['registros']);

echo "CRUD genérico\n";
$antes=$n('clientes');
[, $r]=llamar($api.'crear',['tabla'=>'clientes','datos'=>['nombre'=>'Aerolínea Prueba','pais'=>'Chile','email'=>'a@prueba.cl']]);
prueba('crear un cliente',($r['ok']??false) && $n('clientes')===$antes+1);
$id=llamar($api.'tabla&tabla=clientes')[1]['registros'][0]['identificador'];
[, $r]=llamar($api.'actualizar',['tabla'=>'clientes','id'=>$id,'datos'=>['pais'=>'Perú']]);
prueba('actualizar el cliente',($r['ok']??false) && llamar($api.'tabla&tabla=clientes')[1]['registros'][0]['pais']==='Perú');
[, $r]=llamar($api.'eliminar',['tabla'=>'clientes','id'=>$id]);
prueba('eliminar el cliente',($r['ok']??false) && $n('clientes')===$antes);
[$c,]=llamar($api.'tabla&tabla=clientes;DROP');
prueba('tabla inexistente rechazada (400)',$c===400);

echo "Adaptación del modelo\n";
[, $r]=llamar($api.'agregar_campo',['tabla'=>'clientes','nombre'=>'segmento','tipo'=>'TEXT']);
prueba('agregar un campo',($r['ok']??false));
[$c,]=llamar($api.'agregar_campo',['tabla'=>'clientes','nombre'=>'segmento','tipo'=>'TEXT']);
prueba('campo repetido rechazado',$c===400);
[$c,]=llamar($api.'agregar_campo',['tabla'=>'clientes','nombre'=>'x; DROP TABLE clientes','tipo'=>'TEXT']);
prueba('nombre con SQL rechazado',$c===400);
[$c,]=llamar($api.'agregar_campo',['tabla'=>'clientes','nombre'=>'otro','tipo'=>'BLOB']);
prueba('tipo no permitido rechazado',$c===400);
[, $r]=llamar($api.'crear_tabla',['nombre'=>'aeronaves','campos'=>[['nombre'=>'matricula','tipo'=>'TEXT'],['nombre'=>'horas','tipo'=>'REAL']]]);
prueba('crear una tabla',($r['ok']??false));
[, $r]=llamar($api.'crear_vista',['nombre'=>'v_facturacion','sql'=>'SELECT c.nombre, SUM(p.total) AS total FROM pedidos p JOIN clientes c ON c.identificador=p.cliente_id GROUP BY c.nombre']);
prueba('crear una vista',($r['ok']??false));
[$c,]=llamar($api.'crear_vista',['nombre'=>'v_mala','sql'=>'SELECT * FROM no_existe']);
prueba('vista sobre tabla inexistente rechazada',$c===400);
[$c,]=llamar($api.'crear_vista',['nombre'=>'v_borra','sql'=>'DELETE FROM clientes']);
prueba('vista que no es SELECT rechazada',$c===400);
$m=llamar($api.'modelo')[1];
prueba('el modelo lista la vista y la tabla nueva',in_array('v_facturacion',array_column($m['vistas'],'name')) && in_array('aeronaves',array_column($m['tablas'],'tabla')));

echo "Consola SQL\n";
[, $r]=llamar($api.'consulta',['sql'=>'SELECT * FROM v_facturacion']);
prueba('consulta sobre la vista',count($r['registros'] ?? [])>0);
[$c,]=llamar($api.'consulta',['sql'=>'DELETE FROM clientes']);
prueba('DELETE rechazado',$c===400);
[$c,]=llamar($api.'consulta',['sql'=>'SELECT 1; DROP TABLE clientes']);
prueba('dos sentencias rechazadas',$c===400);
[, $r]=llamar($api.'consulta',['sql'=>'SELECT identificador FROM pedidos WHERE total > :minimo','parametros'=>['minimo'=>'400000000']]);
prueba('parámetro numérico enlazado',count($r['registros'] ?? [])>0 && count($r['registros'])<$n('pedidos'));
[, $r]=llamar($api.'consulta',['sql'=>'SELECT * FROM clientes WHERE nombre = :c','parametros'=>['c'=>"x' OR '1'='1"]]);
prueba('inyección por parámetro no devuelve filas',($r['registros'] ?? null)===[]);
[$c,]=llamar($api.'consulta',['sql'=>'SELECT :a']);
prueba('parámetro sin valor rechazado',$c===400);

echo "Procedimientos\n";
$p0=$n('pedidos'); $l0=$n('lineaspedido');
[, $r]=llamar($api.'procedimiento&nombre=nuevo_pedido',['cliente_id'=>1,'fecha'=>'2026-11-18','lineas'=>[['producto_id'=>1,'cantidad'=>2],['producto_id'=>2,'cantidad'=>1]]]);
$esperado=2*89000000+125000000;
prueba('nuevo pedido calcula el total en el servidor',($r['ok']??false) && abs($r['total']-$esperado)<1);
prueba('el pedido y sus 2 líneas se guardaron',$n('pedidos')===$p0+1 && $n('lineaspedido')===$l0+2);
$p0=$n('pedidos'); $l0=$n('lineaspedido');
[$c,]=llamar($api.'procedimiento&nombre=nuevo_pedido',['cliente_id'=>1,'fecha'=>'2026-11-18','lineas'=>[['producto_id'=>1,'cantidad'=>1],['producto_id'=>999,'cantidad'=>1]]]);
prueba('pedido con producto inexistente rechazado',$c===400);
prueba('la transacción deshizo todo (sin pedido ni líneas)',$n('pedidos')===$p0 && $n('lineaspedido')===$l0);
[$c,]=llamar($api.'procedimiento&nombre=nuevo_pedido',['cliente_id'=>1,'fecha'=>'31-02-2026','lineas'=>[['producto_id'=>1,'cantidad'=>1]]]);
prueba('fecha no válida rechazada',$c===400);
[$c,]=llamar($api.'procedimiento&nombre=nuevo_pedido',['cliente_id'=>1,'fecha'=>'2026-11-18','lineas'=>[['producto_id'=>1,'cantidad'=>0]]]);
prueba('cantidad 0 rechazada',$c===400);

echo "Integración (entrada)\n";
$cuerpo=['tabla'=>'clientes','clave_unica'=>'email','registros'=>[['nombre'=>'Externo','email'=>'ext@otro.com','pais'=>'Sin indicar','campo_raro'=>'x']]];
[$c,]=llamar('/servicios/entrada.php',$cuerpo);
prueba('sin clave: 401',$c===401);
[$c,]=llamar('/servicios/entrada.php',$cuerpo,['X-Clave-Api: mala']);
prueba('clave incorrecta: 401',$c===401);
[, $r]=llamar('/servicios/entrada.php',$cuerpo,["X-Clave-Api: $clave"]);
prueba('con clave inserta el registro',($r['insertados']??0)===1);
[, $r]=llamar('/servicios/entrada.php',$cuerpo,["X-Clave-Api: $clave"]);
prueba('repetir el envío no duplica (clave única)',($r['insertados']??1)===0 && ($r['omitidos']??0)===1);
[$c,]=llamar('/servicios/entrada.php',['tabla'=>'sqlite_master','registros'=>[]],["X-Clave-Api: $clave"]);
prueba('tabla no permitida rechazada',$c===400);

proc_terminate($servidor); proc_close($servidor);
array_map('unlink',glob("$tmp/*")); rmdir($tmp);
echo "\n".($total-$fallos)." de $total pruebas correctas".($fallos?" · $fallos FALLAN":'')."\n";
exit($fallos?1:0);

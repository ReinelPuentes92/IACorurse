Se levanto el ambiente qdrant, a traves de un docker compose docker-compose.yml.
Este archivo es el que levanta el servicio de qdrant.

/* Modelos de embedings */
* A mayor cantidad de dimensiones, mayor cantidad de informacion.
* Si la data es muy grande, tambien conviene el modelo de embedings tenga mayor dimension.
* Se exportan los embendings a un archivo .parquet.
# Screenshots wizard

Este complemento proporciona un asistente para tomar capturas de toda la pantalla o areas específicas como objetos, ventanas, etc. Se activa con la tecla _imprimir pantalla_ que en los teclados estándar suele ser la primera del grupo de tres a la derecha de F12. Si se prefiere usar ottra se puede configurar en las preferencias de NVDA, gestos de entrada.

Cuando se invoca el asistente se crea un rectángulo virtual alrededor del objeto con el foco y se activa una capa de órdenes de teclado con los siguientes

### comandos

* F1 muestra un mensaje de ayuda con los comandos básicos; pulsado dos veces rápidamente abre este documento.

#### Información del rectángulo

Las teclas del 1 al 7 proporcionan la siguiente información:

* 1: Coordenadas de las esquinas superior izquierda e inferior derecha.
* 2: Dimensiones del rectángulo, ancho por alto.
* 3: El objeto de referencia.
* 4: Proporción del área del rectángulo ocupada por el objeto de referencia.
* 5: Indica si parte del objeto de referencia queda fuera del rectángulo.
* 6: Indica si el rectángulo sobrepasa los límites de la ventana activa en primer plano.
* 7: Proporción de la pantalla  ocupada por el rectángulo.

La tecla espacio lee toda esta información seguida.

#### Selección de objetos

El objeto de referencia es el objeto de la pantalla que en cada momento quede delimitado por el rectángulo. En principio este objeto será el que tenga el foco del sistema pero puede seleccionarse otro con las siguienhtes teclas:

* Flecha arriba: encuadra el contenedor del objeto actual.
* F: Encuadra el objeto con el foco.
* N: Encuadra el objeto en el navegador de objetos.
* W: Encuadra la ventana activa en primer plano.
* M: encuadra el objeto bajo el puntero del ratón.
* S: Encuadra la pantalla completa.

Con flecha abajo se deshacen los cambios.

#### Tamaño del  rectángulo

El tamaño del rectángulo se puede modificar usando las siguientes teclas:

* Con mayúsculas+flechas se mueve la esquina superior izquierda:
	* mayúsculas + flecha arriba  o abajo desplaza el borde superior,
	* mayúsculas + flecha izquierda o derecha desplaza el borde izquierdo.
* Con conrol+flechas se mueve la esquina inferior derecha:
	* control + flecha arriba o abajo desplaza el borde inferior,
	* control + flecha derecha o izquierda desplaza el borde derecho.
* control + mayúsculas + flecha arriba expande el rectángulo, moviendo los cuatro bordes hacia afuera.
* control + mayúsculas + flecha abajo contrae el rectángulo, moviendo los cuatro bordes hacia adentro.

La cantidad de píxeles para estos movimientos se puede modificar con las teclas avance y retroceso de página. También en las preferencias.

Al modificar el tamaño del rectángulo el objeto de referencia puede cambiar. Se intentará seleccionar siempre el objeto que esté centrado, en primer plano y que ocupe un área mayor dentro del rectángulo. Los cambios de objeto se anunciarán cuando se produzcan.

#### OCR

Pressing R will recognize the text included in the rectangle. This may not work in some circumstances, for example if the rectangle is too small or if the Bluetooth audio plugin is installed (there is a rare incompatibility).

#### Capturar la imagen

Con la tecla enter se captura la imagen del área de la pantalla delimitada por el rectángulo, se guarda en un archivo y se sale del asistente.

Con mayúsculas+enter en lugar de sólo enter se mostrará un diálogo para elegir dónde guardar la captura en lugar de guardarla automáticamente  en la carpeta predefinida.

Con la tecla escape se cancela y sale del asistente.

### Configuración

En las preferencias de NVDA, opciones, se pueden configurar los siguienhtes ajustes:

* La carpeta donde se guardarán los archivos. Por defecto la carpeta de documentos del usuario.
* El formato del archivo de imagen.
* Si se debe o no ampliar la imagen capturada. La escala se calcula en función del tamaño del rectángulo y de la pantalla. Las imágenes pequeñas se ampliarán más, a un máximo de 4x, y las mayores sólo hasta el límite de la pantalla.
* La acción después de guardar (nada, abrir la carpeta o abrir el archivo).
* La cantidad de píxeles de cada movimiento.


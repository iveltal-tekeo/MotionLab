# Registro de cambios

Las notas de las versiones anteriores a la 0.5.1 están en [CHANGELOG.md](CHANGELOG.md), en inglés.

Qué cambia en cada versión de MotionLab, de la más nueva a la más antigua, desde la 0.5.1. Con la app en español
(*Ajustes > General > Idioma*), *Novedades* y el botón **Actualización disponible** muestran estas notas; una versión
que no está aquí sale en inglés. Números de versión: una `0.x.0` nueva es un gran paso; una `0.x.y` añade algo más
pequeño; una `0.x.y.z` de cuatro partes es un paso pequeño entre ellas (arreglos, mantenimiento, pulido).

## Unreleased

Vídeos más rápidos (0.5.3, construido; se publica cuando las nuevas pruebas muestren la mitad del tiempo de Claude con
los mismos resultados):
- **El Generador pregunta lo que Claude antes adivinaba**: un look para los gráficos (Editorial cálido, Señal suiza,
  Edición nocturna o Sorpréndeme) y *La canción de la última vez* junto a la canción. Todo opcional: si lo dejas,
  Claude elige.
- **Claude empieza desde un resumen**: al guardar una petición, MotionLab escribe en una sola página todo lo que Claude
  necesita (los beats de la canción, las plantillas que encajan con tus palabras, tus valoraciones como reglas, las
  lecciones para ese tipo de vídeo) y dice lo que ha dejado fuera, para que no se pierda nada.
- **Un solo montaje en vez de muchos pasos**: gráficos, efectos de sonido, el vídeo, las comprobaciones y una hoja con
  cada corte, de una vez; solo se vuelven a renderizar los gráficos que cambian, varios a la vez. Los renders finales
  largos van como tareas en la página de Tareas.
- **Menos rondas de revisión**: el texto que se sale del encuadre se marca en la primera captura, los efectos de sonido
  salen a niveles que pasan la comprobación, los movimientos de las plantillas caen en el beat según su tiempo medido,
  y cada plantilla se comprueba en vertical y en cuadrado.
- **Vídeos hablados**: los subtítulos mantienen las palabras de tu guion, la voz se nivela por toma, se evitan los
  destellos negros de las grabaciones de pantalla, y Claude edita con una lista corta en vez de un programa largo.
- **Revisión**: *Enviar a Claude* ahora dice qué partes cambiará la siguiente versión.
- **Lo que ha costado** muestra cuánto del tiempo de Claude fue esperar a las herramientas del laboratorio.

## 0.5.2 - 2026-10-22 - Nueva edición paso a paso, y una app más ligera

- **Nueva edición, paso a paso**: *Editor > Nueva edición* es ahora una ventana de seis pasos numerados sobre una
  línea, uno cada vez: 1 Clips, 2 Texto, 3 Referencias, 4 Estilo, 5 Sonido, 6 Final. Solo hacen falta los clips: deja
  el resto en Auto y Claude decide. Atrás y Siguiente abajo, un ✓ en cada paso que has respondido, y un clic en un
  paso te lleva a él.
- **Tus clips como imágenes**: el paso 1 muestra cada clip del vídeo como un fotograma con su duración: reprodúcelo,
  suelta más o quita uno (a la Papelera de reciclaje, después de un sí). Al elegir un vídeo anterior ves cuántos clips
  tiene.
- **Texto**: de qué va el vídeo y las palabras en pantalla, uno al lado del otro, o un guion o un brief de Preparar.
- **Referencias**: hasta 3 vídeos que has analizado, como tarjetas con su imagen y su duración: sigue su estilo o haz
  una copia exacta.
- **Estilo**: los estilos listos en una fila, unas pocas preguntas cortas (dónde se grabó, qué tipo de vídeo, el
  ritmo, el ambiente, los subtítulos) con 4 respuestas cada una y + para el resto, y una paleta de colores grande para
  los gráficos animados: 7 paletas listas o tus propios colores.
- **Sonido**: la música (la canción del propio vídeo, una canción que eliges, el sonido tal como se grabó, o hablando
  con las pausas cortadas), cuántos efectos de sonido y de qué tipos.
- **Final**: la duración y el formato para cada plataforma, un resumen de todos los pasos (haz clic en uno para
  cambiarlo) y más o menos cuánto tardará Claude. Claude lee primero todo lo que has elegido y lo sigue paso a paso;
  el borrador rápido sigue las referencias, el estilo, tus palabras, la duración, el formato y la música.
- **Un guion en tres pestañas**: la ventana de un guion se abre en **Guion**: el texto entero (ya no hay *Ver todo*),
  su ritmo como una barra de sus partes y sus segundos, y al lado los planos que grabar y el texto en pantalla, cada
  uno del color de su parte. **Revisiones** tiene la comprobación, la revisión de Claude y otra vez el guion con la
  parte que estás revisando resaltada; el consejo de Claude para esa parte está en tu propia revisión. **Detalles**
  tiene el resto. Los prompts tienen las mismas tres pestañas.
- **El camino de un guion**: 1 El guion, 2 Grábalo, 3 Edítalo, 4 Publícalo sobre una línea: lo hecho lleva un ✓, el
  siguiente paso se ilumina y su botón está al final. *Grábalo* muestra la misma línea, y su último paso tiene *Hazlo
  con Claude* a la izquierda y el borrador rápido a la derecha.
- **Inicio y la memoria de Claude, más ligeros**: *Inicio* termina con la hoja de ruta (sin la línea de la memoria de
  Claude ni el panel de estado). La memoria de Claude se queda con Resumen, Lecciones y Conocimiento compartido; las
  pestañas Vídeos, Efectos y Gráficos y efectos guardados ya no están. Claude lo sigue leyendo todo, y tus gráficos y
  efectos guardados siguen en la biblioteca. Motion Graphics ha bajado al final de la barra lateral, encima de Tareas.
- **La hoja de ruta, planificada de nuevo**: la 0.5.3 vídeos más rápidos (con el tiempo de Claude en revisiones,
  guiones y vídeos), la 0.5.4 **Sonido** (efectos de sonido grabados de verdad, música y ambiente de bibliotecas
  gratuitas, una voz en off), la 0.5.5 **Agencia de contenido** (una página *Mi marca*: tu objetivo, tu público, tu
  imagen y tus productos), la 0.5.6 packs de plantillas, la 0.5.7 color + DaVinci Resolve, la 0.5.8 generación de
  contenido y la 0.5.9 el modo yapping; la 0.6.0 es ahora *Tomar notas de vídeos*. El generador de prompts y las
  plantillas por sensación salen del plan.
- **Detalles pequeños**: más espacio alrededor de la fila de "vídeos descargados" del Analizador.

## 0.5.1 - 2026-10-19 - Empieza la fase 2: MotionLab en español, análisis en la mitad de tiempo, la instalación en un solo archivo y una sola forma de revisar

- **Aquí empieza la fase 2**: el camino de la 0.5.0 a la 1.0.0, el despliegue. La fase 1 fue todo hasta la 0.5.0.1.
  La hoja de ruta de *Inicio* muestra las dos fases, y cada versión prevista sube un número: el modo yapping es ahora
  la 0.5.2, los vídeos más rápidos la 0.5.3, el generador de prompts la 0.5.4, los packs de plantillas la 0.5.5, el
  color + DaVinci Resolve la 0.5.6 y la generación de contenido la 0.5.7.
- **Español**: en *Ajustes > General > Idioma* eliges English o Español (España, tú). Con un clic, la app se recarga en
  ese idioma: todas las páginas, los diálogos, los mensajes y las comprobaciones, las fechas ("hace 2 días"), los
  números (4,5) y los recuentos, los nombres y los ajustes de las plantillas de Motion Graphics, el informe de un vídeo
  y, desde esta versión, *Novedades*. En un Windows en español, el instalador también te habla en español, y el
  MotionLab que instala arranca en español. Claude te responde en español en todas las ventanas que abre la app; lo
  que guarda en MotionLab (revisiones, lecciones, su memoria) se queda en inglés, para que lo que compartes se lea
  igual para tus amigos.
- **Instalar es un solo archivo**: *Install-MotionLab.cmd*. Descárgalo, haz doble clic, responde dos preguntas cortas
  (los gráficos animados y tu nombre) y acepta. Instala Git, Python, ffmpeg, Claude Code (e inicia tu sesión), el resto
  de programas y el propio MotionLab de una vez, sin terminal, sin comandos que escribir y sin "abre otra ventana y
  vuelve a ejecutarlo", y abre MotionLab al terminar, con un icono en el escritorio y en el menú Inicio. Antes te dice
  qué va a instalar, cuánto ocupa cada parte y dónde te pedirá permiso Windows; empiezas con la última versión probada
  (la que instala el botón de actualizar). Vuelve a ejecutarlo (o setup.bat) cuando quieras: solo hace lo que falta. El
  README tiene los 3 pasos, en inglés y en español.
- **setup.bat repara**: una copia descargada como ZIP se conecta sola a GitHub (las actualizaciones funcionan), un
  programa que falta se instala después de preguntarte, y *Ajustes > Conectar con GitHub* ya viene rellenado.
- **Tres formas de entrar al Analizador**, como en Preparar: **Vídeos**, **Miniaturas** y la nueva **Guiones y
  prompts**. Cada una dice qué hay y qué no ha revisado Claude todavía, y cada tipo tiene su pestaña debajo. En
  *Inicio*, la primera tarjeta es *Analizar lo que funciona*: Vídeos, Miniaturas, Guiones.
- **Guiones y prompts**: pega o suelta hasta 20 a la vez: guiones para hablar a cámara, ganchos, prompts para
  herramientas de vídeo e imagen con IA, briefs (.txt, .md, .docx, .pdf). MotionLab los numera y los mide al momento (su
  tipo, su longitud, las palabras que comparten, los gemelos); después, una ventana de Claude revisa cada uno, parte por
  parte, y dice qué tienen en común, y tú marcas cada patrón como Correcto / En parte / Incorrecto. Viven en tu
  biblioteca de prompts, así que Optimizar, Grábalo y tus valoraciones también funcionan con ellos.
- **Claude cita, no inventa**: Claude ya no puede ponerle palabras en la boca a tu prompt. Cada parte que cita de un
  prompt o de un guion se comprueba con el texto antes de guardarla (una paráfrasis, trozos desordenados o palabras de
  otro prompt se devuelven), y MotionLab guarda las palabras exactas y dónde están.
- **Conocimiento compartido**: la Memoria de Claude tiene su propia pestaña para lo que compartes con tus amigos y lo
  que llega de ellos. Marca lo que va en tu próximo envío (lo que tiene nombre de prueba se queda en tu PC hasta que lo
  marques, y se avisa de una lección que nombra un archivo de tu PC), mira lo que compartiste antes y, por amigo, sus
  vídeos, sus lecciones pendientes de revisión y las reglas que vienen de él. Todo lo que comparte un amigo lleva una
  etiqueta lima "de <nombre>".
- **Al estilo de**: cada selector de estilo muestra solo los vídeos que analizaste en este PC, con su imagen y un nombre
  que una persona usaría (se acabaron los "Video by ..." o "[VLDJ_-wrwj8]"); en Preparar también puedes elegir tus
  propios guiones y ganchos.
- **Recuentos honestos**: "efectos que has confirmado" cuenta ahora solo tus propios veredictos (los de tus amigos se
  cuentan aparte, así que puede bajar: en un PC con solo vídeos de amigos sale 0), y Claude te avisa cuando algo que ha
  hecho viene del conocimiento de un amigo.
- **Nombres que una persona usaría**: el Analizador y la página de un vídeo muestran el nombre que le diste, el nombre
  que le puso Claude o su título sin el "[VLDJ_-wrwj8]", en lugar del nombre del archivo (pasa el puntero por el nombre
  para ver el del archivo); el Estado de *Inicio* lista tus ediciones con los nombres que les diste, y la lista de
  Tareas y el diálogo de Eliminar también los usan.
- **Claude recuerda tus guiones y prompts**: la Memoria de Claude incluye ahora los conjuntos de guiones y prompts que
  analizaste y los patrones que marcaste como correctos (nunca se comparten); al escribir un guion o un título, Claude
  lee una memoria más corta, sin cómo se hicieron los efectos.
- **Una sola forma de revisar**: revisar se ve y funciona igual en todas partes (los efectos y los posibles fallos de un
  vídeo analizado, la Revisión de un vídeo en el Editor y en el Generador, un guion o un prompt, un título, un conjunto
  de miniaturas, un conjunto de guiones y prompts): lo que juzgas a la izquierda, tu revisión a la derecha, los mismos
  botones ✓ ~ ✗ (teclas 1 2 3, J K para moverte), una nota que se guarda mientras escribes, "N de M revisados" y un
  último paso: Enviar a Claude.
- **¿Acierta Claude?** en guiones y prompts: di si la revisión de Claude de cada parte es correcta (Correcto / En parte
  / Incorrecto); Claude sigue tus veredictos cuando los mejora. Pasa el puntero por una parte para ver sus palabras
  marcadas en el texto.
- Conjuntos de miniaturas y de guiones y prompts: tu nota en cada patrón se guarda, y *Enviar a Claude* vuelve a mirar
  los patrones con tus veredictos: mantiene los que marcaste como correctos y arregla o quita el resto. Un vídeo hecho
  en el Generador lo mejora la propia habilidad de Claude del Generador.
- Posibles fallos: "✓ No es un efecto" es ahora el primer botón (tecla 1) y "★ Es un efecto" el segundo (tecla 2).
- Preparar lista solo tus propios guiones: los guiones de otros creadores que analizas se quedan en su conjunto y en la
  biblioteca de prompts.
- MotionLab lee el texto de un PDF por sí mismo cuando la actualización instala su lector de PDF (hasta entonces, los
  PDF los lee Claude, como antes).
- **Claude arranca más ligero**: las notas que lee primero cada ventana de Claude son casi un tercio más cortas (las
  mismas reglas), Claude lee sus notas sobre una página de la app solo cuando cambia esa página, un ayudante lee solo
  la parte de una habilidad que necesita, y cuatro habilidades de Claude de MotionLab habían perdido su descripción, así
  que pedir algo con tus propias palabras ("aplica este feedback", "rehaz mis clips como este vídeo") podía no
  encontrarlas: ya están de vuelta.
- **Los análisis tardan más o menos la mitad**: la medición usa ahora varios núcleos de tu PC para medir varios
  fotogramas a la vez y escucha la música al mismo tiempo, y la imagen de resumen y el archivo de números se escriben
  más rápido (un vídeo de prueba de 30 segundos: de 35 s a 19 s). Los resultados son los mismos que antes.
- **Abre antes**: tras el doble clic, la ventana aparece unos 3 segundos antes (MotionLab ya no espera primero a dos
  comprobaciones lentas de su propio puerto), y el reinicio después de una actualización es unos 5 segundos más corto.
- **Páginas más rápidas**: *Inicio* y la Memoria de Claude responden varias veces más rápido: las plantillas de Motion
  Graphics ya no se calculan ahí para luego dejarlas fuera. Las pestañas de Motion Graphics y el diálogo de gráficos del
  Generador rehacen el catálogo solo cuando cambia una plantilla o un pack.
- **Aprendido de, con cientos de clips**: las imágenes de los clips se cargan mientras te desplazas, y un clip se carga
  solo cuando pasas el puntero por encima.
- **Más ligero en segundo plano**: con la app abierta, ya no arranca PowerShell cada 20 segundos para preguntar si
  DaVinci Resolve está en marcha; mira la lista de programas abiertos (PowerShell solo mientras Resolve está abierto).
- Arreglos: una nota en una parte de un vídeo ya no se pierde si haces clic fuera sin pulsar Enter; todos los botones
  de Claude fallaban cuando el nombre de usuario de Windows o la carpeta de MotionLab tenía un acento (José, María); un
  programa instalado con MotionLab cerrado se encuentra en el siguiente arranque sin cerrar sesión; *Actualizar yt-dlp*
  ya no se trae una segunda copia de ffmpeg; las pistas de "cómo conseguirlo" apuntan a setup.bat en lugar de a
  comandos de terminal; un arranque que falla (por ejemplo, después de una actualización cuyo paso de instalación se
  rompió) se escribe ahora en el registro de la app, para que *Informar de un problema* y Claude vean por qué; el error
  de ffmpeg llega ahora al registro de la tarea cuando el nombre de un vídeo o de una canción lleva letras como Á o Í
  (antes salía un error de Python); *Generar un prompt nuevo* y *Úsalo, cambia…* le pasan tus palabras a Claude
  enteras: un deseo largo perdía el final (y el estilo que elegiste), y signos como %, &, < o > se perdían por el
  camino.
- Arreglos en los análisis: un vídeo dañado ya no puede dejar colgado para siempre un análisis (ni la preparación de tu
  material para una edición); cuando un vídeo se sustituye por otro con el mismo nombre de archivo, su nuevo análisis ya
  no reutiliza el sonido ni la copia de fotogramas del vídeo anterior; las medidas de simetría de espejo y de mosaico
  repetido dan ahora exactamente los mismos números en cada ejecución.
- Para desarrolladores: las pruebas de la interfaz (smoke, la prueba de actualización, `tools\dev\cdp.py`) usan puertos
  libres y un perfil de navegador propio, así que pueden ejecutarse dos a la vez; un navegador que no arranca falla al
  momento en lugar de a los 2,5 minutos; las 75 capturas de gráficos animados de la autoprueba se hacen de 4 en 4.
  `tools\dev\i18n_check.py` comprueba las traducciones (cada texto tiene su español, con sus marcadores y etiquetas, y
  no sobra ninguno), lista el trabajo de cada área y une los archivos de partes; smoke.py lo ejecuta y abre *Inicio*
  una vez en español.

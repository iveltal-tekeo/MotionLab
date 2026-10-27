# Registro de cambios

Las notas de las versiones anteriores a la 0.5.1 están en [CHANGELOG.md](CHANGELOG.md), en inglés.

Qué cambia en cada versión de MotionLab, de la más nueva a la más antigua, desde la 0.5.1. Con la app en español
(*Ajustes > General > Idioma*), *Novedades* y el botón **Actualización disponible** muestran estas notas; una versión
que no está aquí sale en inglés. Números de versión: una `0.x.0` nueva es un gran paso; una `0.x.y` añade algo más
pequeño; una `0.x.y.z` de cuatro partes es un paso pequeño entre ellas (arreglos, mantenimiento, pulido).

## Unreleased

- **El Analizador: tres formas de aprender de un vídeo.** *Efectos y animaciones* (lo que hacía hasta ahora),
  *Creación de contenido* (próximamente: por qué funciona un vídeo y por qué se hizo viral) y **Notas** - cada una con
  su mascota animada: **FLUX** el cristal azul (Animaciones y efectos), **SPARK** la estrella dorada (Creación de
  contenido) e **INDEX** la esfera turquesa (Notas y conocimiento). Flotan, parpadean y reaccionan: pasa el ratón por
  una forma y su mascota responde, mientras corre un análisis o unas notas su mascota se pone a trabajar, y se ilumina
  cuando terminan. Cada forma tiene además su propia página - haz clic en una tarjeta y su mascota te saluda allí
  con sus vídeos; las pestañas bajo las formas siguen mostrándolo todo. Miniaturas y Guiones y prompts quedan en una fila más pequeña debajo; sus botones
  dicen *Analizar miniaturas* y *Analizar guiones y prompts*.
- **Notas de vídeos** (Analizador > Notas > *Tomar notas*): pega enlaces o elige vídeos; los enlaces se descargan
  hasta 720p. MotionLab saca las palabras (los subtítulos de la plataforma o, si no, voz a texto), los fotogramas clave
  donde cambia la pantalla, los capítulos del creador, lo más repetido de YouTube y las partes patrocinadas
  (SponsorBlock); después Claude escribe las notas solo - un resumen, 3-7 ideas clave, las secciones, los pasos de un
  tutorial, qué aplicar, los recursos que enlaza la descripción y un bloque de contexto para otra IA. Cada punto va
  unido a las palabras del vídeo (o a un fotograma que muestra) con fotograma + código de tiempo, y un clic reproduce
  ese momento; no se guarda nada si una cita no está en el vídeo. Escribe tus propias notas al lado, marca las acciones,
  descárgalo todo en Markdown (con la transcripción si quieres) o cópialo para otra IA. *Borrar el vídeo, guardar las
  notas* libera el espacio cuando termines.
- Los números de un vídeo ahora guardan también sus compartidos y guardados (TikTok da los dos).

## 0.6.0.4 - 2026-10-27 - En el plano: B-roll en tus palabras, gráficos detrás de ti

- **Lo importante sigue en el encuadre**: un clip horizontal en un vídeo vertical se cortaba por el centro; ahora el
  catálogo encuentra el sujeto de cada plano (una cara, si no lo que más llama la atención) y el recorte, y cualquier
  punch-in, se centran en él.
- **Clips HDR del iPhone con su color real**: los clips grabados en HDR (lo que graba un iPhone por defecto) se
  convierten a colores de vídeo normales en vez de salir planos y desvaídos (unas 3 veces el color y el contraste que
  tenían).
- **Más variedad en los borradores rápidos**: un borrador rápido ya no usa el mismo plano dos veces ni la misma escena
  una y otra vez: con 36 clips de prueba, un borrador de 30 segundos pasó de 18 a 26 escenas distintas en 28 planos.
- **Los planos antes del render**: con muchos clips, Claude ahora coloca cada plano de una edición tal como se verá,
  antes de renderizar nada, arregla lo que está mal (una parte borrosa u oscura, el mismo plano dos veces, una cara
  cortada) y te enseña la hoja primero.
- **El B-roll en las palabras que muestra**: en un vídeo hablado, el B-roll ahora entra en la palabra que muestra
  (dices «post» y el móvil con tu post aparece un cuarto de segundo después) o justo en un corte de salto para
  taparlo. Cada inserto dura de 2 a 4 segundos, tu cara se queda con el gancho y el final, nunca hay un destello de
  cara entre dos insertos y como mucho se cubre el 40 % del vídeo: reglas sacadas de guías de edición de creadores en
  vez de un temporizador fijo. Tu voz sigue debajo del B-roll, sin cortes y sin cambiarla por el sonido del clip.
- **Los clips con música son B-roll, no habla**: un clip con una canción o mucho ruido de fondo junto a tu toma
  hablada se tomaba por otra toma hablada, así que el borrador lo ponía entero y no añadía B-roll. Los clips que
  nunca hacen pausas ahora cuentan como B-roll.
- **Gráficos que forman parte del plano**: un gráfico sobre alguien a cámara ya no tiene por qué parecer pegado
  encima: una palabra grande puede quedar detrás de tu cabeza y seguir en la pared cuando la cámara hace un punch-in,
  una tarjeta de cristal esmerila la habitación real que hay detrás con una sombra suave, los gráficos toman la
  suavidad y el grano de tu propia cámara, y todo lo que está cerca de tu cabeza se aparta de tu cara. MotionLab te
  localiza a ti y tu cara en cada clip una sola vez (unos 30 ms por fotograma, sin instalar nada); Claude lo usa
  cuando edita un vídeo hablado. La idea viene de los efectos de vídeo para Claude de Vibha Ramprakash.
- **Curvas que ves y moldeas**: el movimiento de un fotograma clave ahora ofrece las curvas que usan los diseñadores
  de motion (Suavizado fácil, Suavizado fuerte, Deslizar y Despegue junto a Entrada / Salida suave, Mantener y Pop),
  cada una dibujada como una curvita, y un gráfico con dos tiradores que arrastras para dar forma a la tuya, como el
  gráfico de After Effects o el plugin Flow. Los efectos de zoom también las usan.
- **Efectos que siguen tu cara**: tres efectos nuevos en el Editor: *Acercarse* (un acercamiento pequeño y rápido a
  tu cara para una palabra: entra deslizándose y sale suave), *Acercamiento lento* (un acercamiento lento mientras la
  habitación se desenfoca) y *Foco* (la habitación se oscurece y tú sigues iluminado). Los zooms son pequeños y suaves,
  y caen sobre tu cara aunque te muevas.
- **Gráficos en el plano, desde el Editor**: el panel de un gráfico tiene *En el plano*: *Detrás de mí*, *Cristal
  esmerilado*, *Fuera de mi cara* y *Pegado a mi cara*. Antes de renderizar nada, la comprobación de planos ahora
  también avisa de un gráfico que te tapa la cara o de una tarjeta que tu cara cortaría, con su fotograma. Un gráfico
  pegado a tu cara se encoge para quedarse dentro del encuadre y fuera de la barra de arriba y de la zona de textos de
  la app en un primer plano.
- **13 plantillas nuevas para vídeos hablados** (a partir de los diseños de Vibha Ramprakash): *Palabra detrás de
  ti*, *Cartel LED detrás de ti*, *Corchetes de enfoque*, *Reloj de cuenta atrás con láminas*, *Garabato de rotulador*,
  *Caja de comentario*, *Toque en Seguir*, *Pila de mensajes*, *Sello de rechazo*, *Interruptores de ajustes*,
  *Gráfica de cristal*, *Lista de tareas* y *Titular con caja*. Cada una sabe su sitio en el plano (la palabra y el
  cartel detrás de ti, los corchetes y el garabato sobre tu cara, las tarjetas en cristal esmerilado, todo fuera de tu
  cara) y Claude puede ponerlas en las palabras que dices («un sello cuando digo "muere"»).
- **Arreglado: un velo gris sobre tu vídeo**: una plantilla de Motion Graphics puesta transparente sobre un vídeo (con
  su propio fondo apagado) ponía su grano de película sobre toda la imagen, un velo gris suave que aplanaba el
  metraje. Ahora el grano no se pone sobre un vídeo; el gráfico toma el grano de tu propia cámara.
- **Arreglado: una palabra fuera de sitio en el Editor**: un gráfico que se ajusta al tamaño de sus palabras (la
  palabra grande detrás de ti) salía desplazado media palabra a la derecha y más abajo en la vista previa del Editor,
  cortado en el borde del encuadre, aunque el vídeo en sí estaba bien. Ahora la vista previa lo muestra donde lo tiene
  el vídeo.

## 0.6.0.3 - 2026-10-27 - Muchos clips: una caché ligera y un catálogo de clips

- **Muchos clips, una fracción del disco**: los clips de un vídeo ahora se leen una sola vez en una copia ligera
  (todos los fotogramas, en pequeño) y solo los fotogramas que tu edición muestra de verdad se preparan a tamaño
  completo, justo antes del render. Probado con 36 clips / 6,5 minutos de material: 2,1 GB en 35 segundos en vez de
  33 GB en 131 segundos, y una edición de 30 segundos con ellos añade unos 2 GB, no 30. Los clips preparados antes
  siguen funcionando igual.
- **Claude conoce tus clips**: con muchos clips, Claude primero hace un catálogo: cada plano dentro de cada clip, las
  partes que sirven y las que hay que dejar fuera (borrosas, movidas, demasiado oscuras), su movimiento de cámara y su
  luz, los planos que se parecen, el día en que se grabó y una línea sobre lo que muestra. Cada paso siguiente lo lee
  en vez de volver a mirar todos los clips, así que las ediciones con mucho B-roll eligen mejores momentos y *Mejorar*
  parte de lo que Claude ya sabe.
- **Borradores rápidos con muchos clips**: un borrador rápido ya no corta a través de un cambio de plano dentro de un
  clip ni pone dos planos parecidos seguidos, y con clips de varios días tiende a mantener su orden.

## 0.6.0.2 - 2026-10-26 - Fotogramas clave y transiciones en el Editor

- **Fotogramas clave en el Editor**: haz clic en un plano y su nueva pestaña *Vídeo* tiene Escala, Posición, Rotación,
  Opacidad y el punto de zoom, cada uno con un ◆. Pon el cabezal en un sitio, pulsa ◆, mueve el cabezal y cambia el
  valor: el plano se mueve entre los dos, como en CapCut y Premiere. Los fotogramas clave salen como rombos sobre el
  plano: arrastra uno a otro momento o haz clic para elegir cómo va el movimiento (Lineal, Entrada suave, Salida suave,
  Entrada y salida suaves, Mantener o Pop, que se pasa un poco y vuelve). Arrastra el nombre de un valor a izquierda o
  derecha y la vista previa lo sigue mientras arrastras.
- **Transiciones entre dos clips**: un + en cada corte, o el nuevo panel *Transiciones*: Fundido, Fundido a negro,
  Fundido a blanco, Destello blanco, Zoom de acercamiento, Zoom de alejamiento, Deslizar, Látigo, Giro, Glitch y Fuga
  de luz. Arrastra los bordes del bloque para su duración, elige una dirección para Deslizar o Látigo, o *Aplicar a
  todos los cortes*. Un clip sin fotogramas de sobra nunca la impide: esos pocos fotogramas quedan congelados y el
  bloque lo marca con rayas.
- **Por qué aquí no**: un efecto o una transición que no puede ir donde está el cabezal dice por qué, justo debajo (un
  tartamudeo en un vídeo hablado, un corte que ya tiene zoom, ningún clip bajo el cabezal...), en gris antes de que
  hagas clic; y la línea de encima de la lista dice dónde está el cabezal. Cambia a medida que mueves el cabezal.
- **Qué añadir, en una barra**: Clips, Sonidos, Gráficos, Efectos y Transiciones son ahora iconos grandes en el lateral
  del panel Añadir, cada uno del color de su pista en la línea de tiempo, en vez de pestañas pequeñas.
- **Arreglos**: la lista de Clips del Editor apilaba los clips unos encima de otros (y su + no hacía nada); un plano
  movido en el Editor dejaba atrás su sacudida; en el Analizador, el panel de una tarea en marcha queda un poco más
  abajo de las tres opciones. Compartir con más seguridad: el zip de efectos de sonido de un amigo ya no puede
  escribir un archivo fuera de su carpeta, y la app ya no muestra archivos fuera de las carpetas que comparte (nunca el
  archivo de tu clave de ElevenLabs).

## 0.6.0.1 - 2026-10-26 - Efectos que funcionan en el Editor

- **Efectos que de verdad puedes añadir**: en el Editor, la mayoría de los efectos se paraban con un error: un plano
  que ya tenía zoom (el zoom lento del borrador rápido en tu primer plano, un zoom hacia un corte) no aceptaba ningún
  acercamiento, alejamiento, punch-in ni sacudida, y un efecto cerca del final de un plano decía que estaba demasiado
  cerca. Ahora un plano admite todos los zooms que quieras, cada uno con su propia pieza en la pista de Efectos que
  arrastras, alargas, haces más fuerte o quitas por separado, y un efecto cerca del final de un plano empieza un poco
  antes para que quepa.
- **Arrastrar un efecto**: una pieza que arrastras más allá del borde de su plano (o contra el zoom de al lado) ahora
  se para en el borde en vez de dar un error, y por fin puedes mover un Punch-in. Un zoom lento vuelve a mostrarse como
  *Zoom de acercamiento*, no como Punch-in.
- **Se acabaron los efectos que no puedes usar**: los efectos que necesitan un clip salen en gris en un vídeo hecho de
  gráficos, y el tartamudeo en un vídeo hablado, con el motivo al pasar el ratón por encima. Un destello o un
  fotograma negro donde no hay ningún clip bajo el cabezal (una tarjeta final) sigue funcionando, como una capa de
  color sobre la imagen.
- **La composición no es un efecto**: el marco de una cámara en la esquina y el fondo de una tarjeta final ya no salen
  en la pista de Efectos, donde moverlos rompía la composición.

## 0.6.0 - 2026-10-26 - Agencia de contenido: Mi marca, el Editor y tu calendario de contenido

- **Agencia de contenido, la versión**: MotionLab ahora conoce tu marca y planifica tus publicaciones. Mi marca (tu
  objetivo, tu público, tus colores, fuentes, logo, tono, productos, subtítulos y cierre, leídos de tu web y luego
  ajustados por ti) entra en cada vídeo, guion y título hecho *Para mi marca*; la Agencia de contenido planifica tus
  publicaciones en un calendario y te enseña cómo les fue; el Editor te deja cambiar cualquier vídeo tú mismo en una
  línea de tiempo; y el sonido ha crecido: efectos de sonido reales y creados con ElevenLabs que eliges de oído, tu
  música y tus ambientes, y cada render al mismo volumen. Todo lo de abajo llegó en esta versión.
- **Mi marca**: una página nueva arriba en la barra lateral, en tres pestañas para no tener que desplazarte: *Resumen*
  (tu web, objetivo, público y perfiles), *Estilo* (identidad de marca, tono, subtítulos y tu estilo de edición como
  tarjetas de vídeo) y *Catálogo* (tus productos). Guarda tu objetivo en redes, para quién son tus vídeos, tu logo,
  los colores y el tono de tu marca, tu web y tu catálogo, cada producto con su precio y un interruptor para decidir
  si Claude puede usarlo en los vídeos. Todo se guarda mientras escribes y se queda en tu PC. Los colores se
  pueden escribir como código hexadecimal (#2eaa5c), el tono tiene su propia tarjeta con palabras rápidas para marcar
  y, cuando añades tu logo, aparece grande y tenue en la franja de color de la página. El nombre de tu marca y lo que
  hace, sus fuentes (títulos y texto) y tus perfiles (YouTube, TikTok, Instagram..., cada uno con su llamada a la
  acción) también tienen su sitio. *Empezar de cero* lo borra todo para volver a probar (se guarda una copia:
  *Recuperarlo* justo después). El catálogo enseña tus productos como tarjetas con su foto (haz clic para poner la
  tuya), su precio y un interruptor *En vídeos*, con *Añadir un producto* arriba.
- **Motion de producto**: el paso Texto de Nueva edición tiene *Mostrar un producto*: elige hasta 2 productos de Mi
  marca y cuándo salen (de pasada, al final o ambos). Claude los crea con una plantilla nueva de Motion Graphics,
  *Tarjeta de producto*: la foto del producto en una tarjeta, su nombre, el precio apareciendo, un botón con tu web y
  tu logo, con los colores y las fuentes de tu marca, en vertical u horizontal, sobre tu vídeo o como tarjeta final.
- **Agencia de contenido: el calendario de contenido**: una fila nueva bajo Mi marca. Planifica tus publicaciones en
  un calendario mensual: cada una con su día y hora, dónde sale (TikTok, Instagram, YouTube...), su fase de idea a
  publicada (un color cada una), el vídeo de MotionLab, el sonido en tendencia para añadir en la app al publicar,
  notas y los enlaces cuando ya está publicada. Arrastra publicaciones entre días o guárdalas como ideas; marca los
  días en que publicas y los vacíos salen como huecos, con "esta semana 2 de 3". *Añadir al Calendario de Windows* te
  avisa una hora antes de cada publicación. **Tus vídeos**: *Revisar mis perfiles* lee tu YouTube y tu TikTok (los
  perfiles de Mi marca: números públicos, sin iniciar sesión, solo cuando lo pulsas) y enseña tus vídeos publicados con
  cuándo salieron, sus visualizaciones, me gusta y comentarios, cuáles fueron mejor de lo habitual y cuánto creció cada
  uno desde la última revisión; el calendario enseña lo que salió cada día. **Importar tus estadísticas**: el archivo
  que descargas de YouTube Studio, TikTok Studio o Meta Business Suite (en inglés o en español) añade a tus vídeos el
  tiempo de visualización, el % visto y los clics, y trae Instagram, que no se puede leer de otra forma. Una
  publicación enseña **cómo le fue** (visualizaciones ahora y a las 48 horas, 7 días y 28 días de salir, según tus
  revisiones), la ganadora de **Probar y comparar**, una lista de **antes de publicar** por plataforma (capítulos, el
  sonido añadido en la app, hashtags, la etiqueta de colaboración pagada...) y qué formato quiere cada plataforma
  frente al de tu vídeo. **Cuándo publicar**: escribe las mejores horas de tu público desde las estadísticas de cada
  plataforma y salen como accesos rápidos en cada publicación (sin ellas, horas genéricas marcadas como tal).
- **Una barra lateral más limpia**: Motion Graphics va encima de Memoria de Claude, y Tareas y Ajustes (ahora con
  un engranaje) se abren desde *Más*, abajo; el número de tareas en marcha sale en *Más*.
- **Más de tu marca**: tu forma de hablar con tus propias palabras (cuatro deslizadores: de formal a cercano, de serio
  a divertido, de respetuoso a descarado, de tranquilo a con energía; las palabras que usas y las que nunca usas;
  frases que suenan a ti), tus pilares de contenido (cada publicación del calendario lleva uno y el calendario enseña el
  reparto del mes), el código promocional de un producto y un interruptor *Colaboración pagada* (Claude lo marca como
  publicidad), y lo que dice tu web: la importación guarda su texto legible para que Claude compruebe los datos.
- **Tu marca de un vistazo**: el Resumen de Mi marca empieza con una tarjeta de lo que *Para mi marca* le da a Claude
  (logo, nombre en tu fuente de títulos, colores, fuentes, tono, perfiles, productos) y tus últimos vídeos hechos con
  *Para mi marca*. En Estilo, *Nombres y palabras* mantiene los nombres escritos exactamente (RIFT en
  mayúsculas...) en subtítulos, guiones y títulos, y la transcripción los reconoce bien.
- **Tus subtítulos**: Mi marca tiene un estilo de subtítulos: el look, la fuente, mayúsculas o no, los colores del
  texto y de la palabra dicha, cómo se mueven las palabras, dónde van y una caja detrás, con vista previa en directo.
  Los subtítulos de Claude lo usan, y el botón Subtítulos de la pestaña Gráficos de un vídeo te lo ofrece.
- **Tu estilo de edición**: elige hasta 3 vídeos que analizaste como la forma de montar los vídeos de tu marca. Nueva
  edición te los ofrece primero como *El estilo de mi marca* y, con *Para mi marca* marcado y sin referencias
  elegidas, Claude y el borrador rápido siguen tu estilo.
- **Tu moodboard**: Mi marca > Estilo tiene un moodboard: suelta imágenes cuyo estilo te encante (guardadas de
  Pinterest o Instagram, capturas, fotos). MotionLab las lee (luz, color, contraste, cuánto aire tienen) y te enseña
  sus colores principales, a un clic de los colores de tu marca. Los vídeos hechos *Para mi marca* siguen la sensación
  del moodboard en sus gráficos y miniaturas; Claude mira las propias imágenes. Se quedan en tu PC.
- **Tu logo en todas sus versiones**: Mi marca > Estilo guarda tu logo para fondos oscuros, para fondos claros y el
  icono solo, y dónde va en tus vídeos (el cierre, también pequeño en una esquina, o en ningún sitio); Claude pone la
  versión que se lee en cada fondo. Bajo tus colores, *¿Se lee bien?* muestra tus colores de texto y de acento sobre
  tu fondo con su contraste, y Claude nunca pone palabras en un color que no se lee.
- **Tu marca en Nueva edición y en los gráficos**: la paleta de colores de Nueva edición ofrece *Mi marca* (tus
  colores, el de acento primero), cada lista de fuentes enseña primero las de tu marca y, con *Para mi marca*
  marcado, el borrador rápido del Generador pinta sus gráficos con tus colores y tus fuentes.
- **Tu cierre**: Mi marca > Estilo te deja elegir cómo terminan tus vídeos: una tarjeta con tu logo, un título con tu
  web o una tarjeta de canal, más tu frase de despedida, con una vista previa en vivo hecha con tu marca. Claude crea
  ese mismo cierre como última escena de un vídeo hecho *Para mi marca* (nunca antes del gancho), y el borrador
  rápido del Generador también. También puede llevar tu propio logo sonoro: un sonido corto que ElevenLabs crea a
  partir de tus palabras (o tu propio archivo), y que suena en el cierre en lugar de los sonidos de la plantilla.
- **Lo que te funcionó**: el tono de Mi marca enseña los ganchos, finales y títulos de los guiones, títulos y vídeos
  que puntuaste como buenos (cada uno abre su guion), y Claude sigue su forma (nunca las mismas palabras) cuando
  escribe para tu marca.
- **Tamaño de los subtítulos y palabras por línea**: el estilo de subtítulos de Mi marca también fija cuántas palabras
  salen a la vez (de 1 a 6) y el tamaño (de pequeño a enorme), y la vista previa enseña ambos; los subtítulos con tu
  estilo los siguen, también cuando siguen tu guion.
- **Datos y archivos de tus productos**: cada producto del catálogo de Mi marca tiene *Datos y archivos*: su
  beneficio principal, lo que Claude puede afirmar (cada cosa con su prueba), lo que nunca debe afirmar y capturas o
  grabaciones de pantalla cortas. Claude solo dice de él lo que dicen.
- **Tu logo en Motion Graphics**: el selector de logos enseña primero tu propio logo (y en *Mi marca*), junto a los de
  la biblioteca; cualquier gráfico con logo puede usarlo, y dibuja solo la versión que se lee en su fondo (la clara
  sobre oscuro, la principal sobre claro). Se queda en tu PC.
- **Tu biblioteca de sonidos**: Motion Graphics tiene una pestaña *Sonidos*: cada sonido grabado de tu PC por tipo, ▶
  para escucharlo, de dónde viene y su licencia; ★ lo hace favorito (su tipo usa primero tus favoritos) y *Ocultar* lo
  deja fuera de tus vídeos. *Añadir sonidos* acepta un pack, una carpeta o unos cuantos archivos: un pack que
  MotionLab conoce se ordena como su propia biblioteca, y el resto por sus nombres. Tus amigos tienen los mismos
  sonidos: MotionLab trae ahora cuatro sonidos libres (CC0) y una lista de qué sonido de qué pack gratuito usa, así
  que al importar ese pack tienen la misma biblioteca. El paso Sonido de *Nueva edición* tiene *Elige los sonidos*:
  escucha y marca los que puede usar un vídeo. **Crear sonidos** con tu propia clave de ElevenLabs: elige cuántos de
  cada tipo (primero los tipos de los que tienes pocos), te dice los créditos que gasta, y los sonidos nuevos esperan
  en *Nuevos* para que marques con estrella los buenos y ocultes el resto. MotionLab ya trae 20: whooshes, látigos,
  pops, clics y teclas creados a partir de descripciones de motion design premium. El plan gratis solo permite un uso
  no comercial, y un vídeo que publiques menciona elevenlabs.io, así que sus sonidos salen como *uso no comercial*;
  los creados con un plan de pago se pueden compartir: *Compartir
  con amigos* crea un archivo para Google Drive, y un amigo lo añade con *Añadir sonidos* > el enlace.
- **Tu música**: Motion Graphics tiene una pestaña *Música*: las canciones que descargas en el Analizador y las que
  añades, cada una medida una vez (su tempo, cuánta energía tiene, su tono y su duración), con ▶ para oírla, ★ y
  Ocultar. Nueva edición enseña tus canciones como tarjetas con los mismos datos, así eliges de oído y por sensación
  en lugar de por el nombre de un archivo.
- **Ambiente bajo tu voz**: una habitación tranquila, un café, una calle o lluvia bajo un vídeo hablado llenan el
  silencio entre tus cortes. Créalo con ElevenLabs (se repite sin que se note el corte) o añade el tuyo; el paso
  Sonido de Nueva edición tiene *Ambiente bajo tu voz*, y se mezcla muy por debajo de tus palabras.
- **El Editor**: una pestaña nueva *Editor* en cada vídeo: una línea de tiempo como la de CapCut, sin ventana de
  Claude. Tus planos en una pista principal que se junta sola, los gráficos y los subtítulos encima, los efectos, los
  efectos de sonido y tu voz (o tu canción) debajo, y una vista previa en directo que reproduce tus cambios antes de
  guardar. Planos: arrastra uno para moverlo, sus bordes para recortarlo (más de su propio clip, o menos), córtalo en el
  cabezal (S), ponlo más lento o más rápido (de ¼× a 4×: su voz mantiene el tono), enseña otro momento de su clip en el
  mismo sitio (Alt + arrastrar), cámbialo por otro clip del vídeo, baja su sonido o siléncialo, bórralo, y añade un
  clip desde la pestaña *Clips*. Un vídeo hecho desde cero tiene sus escenas en esa pista, y se mueven y recortan
  igual. Los efectos (zooms, sacudidas, destellos, transiciones...) son fichas que arrastras, haces más intensas, más
  largas o suavizadas, quitas o añades desde la pestaña *Efectos*. Arrastra gráficos y sonidos a otro momento o
  recórtalos; añade efectos de sonido de tu biblioteca y plantillas de Motion Graphics (arrástralos a la línea de
  tiempo), cambia sus palabras y colores (los colores de tu marca a un clic), sube o baja un sonido o dale otro. Una
  canción: arrástrala para que el vídeo empiece en otro momento de ella, o cambia su volumen. Subtítulos: arrastra uno
  para moverlo o sus bordes para recortarlo (sus palabras siguen al ritmo de la voz; el subtítulo con el que choca le
  deja sitio), divide uno en el cabezal, añade uno, corrige o quita uno y cambia cómo se ven todos: Clásico o Caja
  limpia, fuente, tamaño, posición y colores. *Verlo renderizado* enseña los dos segundos alrededor del cabezal tal
  cual los hará Guardar. Deshacer / rehacer, imán y zoom. *Guardar* crea una versión nueva (la de la que partiste se
  queda), vuelve a cortar tu voz para que encaje y solo rehace lo que cambió. Claude lee lo que cambiaste a mano la
  próxima vez.
- **Las pestañas de un vídeo, cada una con su color**: Resumen, Revisión y Editor llevan su propio icono y color:
  Revisión es violeta (le pasa el vídeo a Claude), el Editor cian (tú, a mano). Bajo el reproductor del Resumen, dos
  caminos en esos colores, *Cámbialo tú* (el Editor) y *Mejóralo con Claude* (Revisión), con *Empezar de nuevo* como
  enlace debajo, y el Editor en la lista lateral del Resumen. Los renders de un vídeo se eligen en una sola lista,
  *Versión seleccionada*; los cambios del Editor, en una lista bajo su botón. El aspecto del Editor, revisado con dos
  comprobadores de diseño (Impeccable y Hallmark): sin degradados ni brillos, el texto pequeño más grande y un marco de
  foco en cada control.
- **Importar desde tu web**: un botón junto a tu web la lee y trae lo que encuentra: el catálogo entero de una tienda
  (Shopify, WooCommerce o los datos de producto marcados en las páginas) con precios, descripciones, fotos y enlaces,
  además de tu logo, colores, fuentes, nombre, descripción y perfiles. Antes, una ventana te enseña todo y adónde
  va cada cosa. Tú marcas lo que entra, y lo que Mi marca ya tiene sale marcado para que nada se añada dos veces. Las
  fuentes de tu web que son gratuitas de Google entran en tus fuentes de este PC, con su licencia, listas para
  títulos y texto. El botón es grande, una barra de progreso enseña cuánto lleva leído y puedes salir de la página:
  si termina mientras estás en otra, MotionLab te avisa, aparece un punto en Mi marca y lo encontrado te espera allí
  hasta que lo importes. Los colores salen de una captura de tu página (lo que ve un visitante), cada uno con su papel
  (fondo, texto, acento) y cuánto ocupa de la página, también los de tu logo y los valores exactos que usa el código
  de tu web.
- **Para mi marca**: Nueva edición, el Generador y los guiones y títulos de Preparar tienen un interruptor *Para mi
  marca*: marcado, Claude lo hace tuyo: tus colores, tu logo en el cierre, tu web en la llamada a la acción, tu tono,
  un final que encaja con tu objetivo y solo los productos que permites, con tus precios. En Nueva edición está
  arriba, con una pequeña vista previa de lo que recibe Claude (tu logo, colores, web, objetivo, productos y tono).
- **Crear en DaVinci**: el último paso de Nueva edición tiene una tarjeta sencilla con el logo de DaVinci Resolve en
  lugar de la casilla de abajo.
- **Más fácil de leer**: el texto gris claro es más claro (ahora se lee bien sobre el fondo oscuro), ningún texto mide
  menos de 11 px, las líneas largas se cortan antes y un párrafo ya no termina con una palabra sola.
- **Un aspecto más limpio**: las tarjetas pierden la franja de color de un lado (ahora un borde fino del mismo color)
  y los botones y tarjetas pierden su brillo de color; el color translúcido de cada sección se queda.
- **Motion graphics más variados**: un vídeo generado ya no tira de las mismas pocas plantillas: cada escena tiene
  la suya (se acabó la plantilla que vuelve una escena sí y otra no), las que usaron tus últimos vídeos se apartan
  salvo que una sea claramente la mejor, y Claude recibe varias opciones para cada línea de tu texto en lugar de una
  lista corta para todo el vídeo. Las ediciones de tus clips en el Editor también: opciones de plantillas nuevas que
  encajan con tu texto o tu guion, y las que usaron tus últimos vídeos se apartan. También menos elecciones raras:
  palabras pequeñas como "up" o "short" ya no traen un gráfico o una plantilla cualquiera, "stream" ya no cuenta como
  "streak", y una línea a la que no le encaja nada recibe texto animado en lugar de un cierre a mitad del vídeo.
- **Un sonido terminado** - cada vídeo que MotionLab renderiza sale ahora con un volumen constante (-14 LUFS, el
  nivel al que lo reproduce YouTube) y con sus picos más altos por debajo de -1 dB después de comprimir el vídeo: se
  acabaron los vídeos hablados que suenan bajos y los chasquidos cuando una plataforma los vuelve a codificar. Un vídeo
  hecho antes lo recibe en su siguiente montaje, sin volver a renderizar la imagen.
- **Sonido en los vídeos hechos desde cero** - un vídeo con efectos de sonido pero sin canción salía mudo; ahora los
  efectos son su sonido.
- **Los efectos de sonido no pisan tus palabras** - en un vídeo hablado, un whoosh, un pop o un golpe que cae sobre
  una palabra suena ahora muy bajo (al menos 22 dB por debajo de tu voz), y uno que cae en una pausa queda al nivel
  justo junto a tu voz; antes salía demasiado fuerte en las pausas.
- **Nada sobre tu cara** - cada montaje de tu vídeo comprueba ahora que ningún subtítulo ni gráfico te tapa la cara
  (medido en los fotogramas, también cuando sales en una ventanita en la esquina) y, en un vídeo vertical, que ninguno
  queda debajo de los botones y textos de la propia app arriba, abajo o en el borde derecho. Claude mueve lo que
  encuentra antes de que veas el vídeo; un gráfico que tiene que ir sobre tu cara (un antes / después) puede quedarse.
  Los subtítulos de lo que dices se colocan ahora solos, plano a plano: bajo tu barbilla si hay sitio y, en un primer
  plano, justo bajo tu boca; nunca sobre tus ojos o tu boca, nunca subidos a tu frente, y fuera de la franja inferior
  de las plataformas.
- **Los vídeos hablados terminan en la palabra** - la construcción avisa cuando un vídeo hablado sigue después de su
  última palabra (una tarjeta final ahí está bien) y cuando tiene más de 4 whooshes en 30 segundos.
- **Subtítulos con palabra clave** - un tercer aspecto junto a Clásico y Caja limpia: una o dos palabras pequeñas con
  UNA palabra clave grande debajo, en tu color de acento y en cursiva con serifa, cada palabra al decirla. Elígelo en
  el estilo de subtítulos de Mi marca o para los subtítulos de un vídeo.

## 0.5.4 - 2026-10-25 - Sonido: efectos de sonido reales, elegidos de oído

- **Sonido, la versión**: cierra la versión de sonido que empezaron la 0.5.3.3 y la 0.5.3.4: efectos de sonido de
  grabaciones reales de tu propia biblioteca de sonidos en lugar de inventados, borradores rápidos que traen sus
  efectos de sonido, una canción desde un enlace con una copia sin ella para publicar. Los siguientes pasos (sonidos
  compartidos con tus amigos, elegir tú los sonidos, una biblioteca de música) llegan con la 0.6.0.
- **Más efectos de sonido grabados, elegidos de oído**: en el PC donde está la biblioteca de sonidos, una tercera
  ronda de escucha añadió sonidos grabados para glitches, brillos (dos glissandos), un móvil vibrando y ticks, y más
  variedad para los movimientos de aire suaves; donde el sonido inventado era el que gustaba (fantasmas, pops, golpes
  de videojuego) se queda. Un sonido no elegido queda apartado, nunca se borra.

## 0.5.3.4 - 2026-10-25 - Una canción desde un enlace

- **Una canción desde un enlace**: el paso *Sonido* de Nueva edición tiene *Desde un enlace…*: pega un enlace de
  TikTok, YouTube o SoundCloud y la canción se descarga como MP3 y queda elegida, así el montaje corta en sus beats.
  Una canción descargada es de otra persona, así que cada render con ella trae también una copia sin la canción:
  *Listo para publicar* la muestra con el punto donde empieza la canción (p. ej. «desde 0:11.63»); añades el mismo
  sonido en TikTok o Instagram y no te silencian la publicación. Tus efectos de sonido siguen en la copia.

## 0.5.3.3 - 2026-10-25 - Efectos de sonido grabados, y borradores rápidos con sonido

- **Efectos de sonido grabados de verdad**: los whoosh, subidas, golpes, clics, pops y sonidos de cámara de tus
  montajes ahora salen de efectos grabados de tu propia biblioteca de sonidos, no solo de sonidos inventados. Cada uno
  cae en su fotograma como antes (el pico del whoosh en el movimiento, el final de la subida en el drop) y cada vez
  suena uno distinto. Claude puede añadir un pack gratuito que descargues; se queda en tu PC. Los tipos que aún no
  tienen nada grabado mantienen el sonido inventado. Además suenan un poco más bajos bajo la canción (2 dB), nunca
  tanto como para que la canción los tape.
- **Los borradores rápidos llegan con efectos de sonido**: un borrador rápido de Nueva edición ahora pone un sonido en
  sus propios efectos: un golpe en el drop y en los destellos, una subida antes de un acelerón, un swish rápido en
  cada zoom de un vídeo hablado. Cuántos y de qué tipos lo decide el paso *Sonido* de Nueva edición (Auto = unos pocos
  en un vídeo hablado, algunos en un montaje musical; Ninguno = ninguno). *Termínalo con Claude* los mantiene.

## 0.5.3.2 - 2026-10-25 - Grábalo te lleva al Editor, y Termínalo con Claude

- **Grábalo te lleva al Editor**: el *Grábalo* de un guion mantiene el teleprompter, las frases y añadir tu grabación;
  su último paso ahora es **Seguir en el Editor**, que abre Nueva edición con tu grabación y el guion ya cargados, así
  que un vídeo hablado tiene todas las opciones de Nueva edición (referencias, estilo, paleta, efectos de sonido,
  duración, formato). El paso *Edítalo* del guion también va directo allí.
- **Termínalo con Claude**: cuando la versión más nueva de un vídeo es un borrador rápido, su página muestra *¿Te
  gustan los cortes? Termínalo con Claude*: marca qué añadir (gráficos animados, subtítulos, efectos de sonido, color;
  ya vienen marcados según lo que elegiste en Nueva edición), di lo que quieras con tus palabras y Claude hace la
  siguiente versión encima del borrador. Los cortes, las transiciones y el ritmo se quedan como están; el borrador
  también.

## 0.5.3.1 - 2026-10-25 - 114 plantillas nuevas de Motion Graphics

- **114 plantillas nuevas de Motion Graphics**: textos que aparecen, gráficas, publicaciones de redes, pantallas de
  apps, un logo que se revela y una transición, hechas por MotionLab con el look Editorial cálido: 189 plantillas en
  total. Cada una usa tus palabras, colores y fuentes, y se reproducen en la vista previa en directo mientras las
  cambias.

## 0.5.3 - 2026-10-24 - Vídeos más rápidos, fotos en tus montajes y una vista previa de tu miniatura

Vídeos más rápidos: Claude hace un vídeo en menos pasos y más cortos:
- **El Generador pregunta lo que Claude antes adivinaba**: un look para los gráficos (Editorial cálido, Señal suiza,
  Edición nocturna o Sorpréndeme) y *La canción de la última vez* junto a la canción. Todo opcional: si lo dejas,
  Claude elige.
- **Claude empieza desde un resumen**: al guardar una petición, MotionLab escribe en una sola página todo lo que Claude
  necesita (los beats de la canción, las plantillas que encajan con tus palabras, tus valoraciones como reglas, las
  lecciones para ese tipo de vídeo) y dice lo que ha dejado fuera, para que no se pierda nada.
- **Un solo montaje en vez de muchos pasos**: gráficos, efectos de sonido, el vídeo, las comprobaciones y una hoja con
  cada corte, de una vez; solo se vuelven a renderizar los gráficos que cambian, varios a la vez. El final pone
  desenfoque de movimiento solo a los gráficos que se mueven (los subtítulos y los gráficos quietos se quedan sin
  él: un final de 60 segundos ha pasado de 13,5 a 6,5 minutos). Los renders finales largos van como tareas en la
  página de Tareas.
- **Menos rondas de revisión**: el texto que se sale del encuadre se marca en la primera captura, los efectos de sonido
  salen a niveles que pasan la comprobación, los movimientos de las plantillas caen en el beat según su tiempo medido,
  y cada plantilla se comprueba en vertical y en cuadrado.
- **Vídeos hablados**: los subtítulos mantienen las palabras de tu guion, la voz se nivela por toma, se evitan los
  destellos negros de las grabaciones de pantalla, y Claude edita con una lista corta en vez de un programa largo.
- **Revisión**: *Enviar a Claude* ahora dice qué partes cambiará la siguiente versión.
- **Lo que ha costado** muestra cuánto del tiempo de Claude fue esperar a las herramientas del laboratorio.

También nuevo, casi todo pedido por un amigo que edita con MotionLab cada día:
- **Fotos en tus montajes**: *Nueva edición > 1. Clips* (y *Grábalo*) aceptan fotos como fotos: JPG, PNG, WebP, HEIC /
  HEIF del iPhone, AVIF, BMP, TIFF, GIF, bien orientadas. Cada una se ve con su propia imagen y una etiqueta amarilla
  FOTO, y un clic en su duración (3 / 5 / 8 s) decide cuánto tiempo se ve. En el montaje una foto es un plano fijo con
  un zoom lento; una foto horizontal en un vídeo vertical puede verse entera sobre una copia desenfocada de sí misma.
  Claude ve una hoja con tus fotos y las coloca en la historia.
- **Añadir una carpeta entera**: *Añadir carpeta…* (o soltar una) toma cada vídeo, foto y canción que hay dentro,
  también en las subcarpetas, en orden. Dos archivos con el mismo nombre de carpetas distintas (el C0001.MP4 de dos
  días) entran los dos.
- **Se acabaron los clips negros de un Mac o un iPhone**: los archivos ocultos "._" que un Mac o un iPhone deja junto
  a tus clips nunca se copian, y los que se copiaron antes ya no aparecen.
- **Cambia el nombre del vídeo nuevo en el paso 1**: su nombre sigue siendo editable después de añadir los clips.
- **Las páginas se actualizan solas**: un render terminado, un guion que ha escrito Claude, un análisis nuevo: aparecen
  en la página que estás mirando en pocos segundos, nunca mientras hay un diálogo abierto o estás escribiendo.
- **NUEVO en todo lo nuevo**: una etiqueta roja NUEVO en los vídeos nuevos (un render terminado), guiones, prompts,
  análisis, conjuntos y gráficos animados; se va al hacer clic en la tarjeta o al pasar a otra sección.
- **Mejorar mi guion deja una sola tarjeta**: mientras Claude trabaja, tu guion pegado aparece como *mejorando…*;
  cuando se guarda la versión nueva, ocupa el lugar de la antigua (la antigua va a la Papelera de reciclaje, nunca una
  que ya hayas grabado).
- **Tus cambios sobreviven a las actualizaciones**: los umbrales ajustados para este PC viven ahora en su propio
  archivo, que las actualizaciones nunca tocan; otros cambios que una actualización sustituye se guardan y vuelven con
  *Recuperarlos*. También se guardan los ajustes que esta versión no conoce.
- **Un botón propio de MotionLab en la barra de tareas**: la ventana y un MotionLab anclado muestran el icono de
  MotionLab, no el de Microsoft Edge.
- **Previsualiza tu miniatura**: *Analizador > Miniaturas* muestra tu miniatura en una copia de la página de Inicio de
  YouTube (y Búsqueda, A continuación, un móvil) junto a los vídeos más nuevos y más vistos de grandes creadores
  (MrBeast, Mark Rober, MKBHD y más; *Canales…* cambia la lista) o junto a las miniaturas que has analizado. Oscuro o
  claro, *Entornar los ojos* para ver qué destaca, *¿Dónde está la mía?*. Tus imágenes no se guardan.
- **Menos zooms en los montajes**: los zooms, los barridos y los empujes guardan ahora la distancia (uno cada pocos
  segundos, uno cada ~8 s en un vídeo hablado) y nunca saltan entre dos planos de la misma toma; un montaje avisa
  cuando lleva demasiados.

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

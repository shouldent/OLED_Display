const Desklet = imports.ui.desklet;
const St = imports.gi.St;
const Util = imports.misc.util;

function JarvisDesklet(metadata) {
    this._init(metadata);
}

JarvisDesklet.prototype = {
    __proto__: Desklet.Desklet.prototype,

    _init: function(metadata) {
        Desklet.Desklet.prototype._init.call(this, metadata);
        
        // metadata.path es la ruta segura y genérica a tu carpeta
        this.path = metadata.path; 
        
        this.container = new St.BoxLayout({vertical: true, style_class: 'jarvis-box'});
        
        this.addButton("Reloj", "set-screen/clock");
        this.addButton("Performance", "set-screen/performance");
        this.addButton("Sensores", "set-screen/sensors");
        this.addButton("Red", "set-screen/net-traffic");
        this.addButton("Calendario", "set-screen/calendar");
        this.addButton("AUTO MODE", "resume-auto");

        this.setContent(this.container);
    },

    addButton: function(label, path) {
        let btn = new St.Button({label: label, style_class: 'jarvis-button'});
        btn.connect('button-release-event', () => {
            // Usamos curl directamente; al estar en el sistema, no necesita ruta absoluta 
            // a menos que sea un entorno muy restringido.
            Util.spawnCommandLine('curl -X POST http://localhost:8000/' + path);
        });
        this.container.add(btn);
    }
};

function main(metadata) {
    return new JarvisDesklet(metadata);
}
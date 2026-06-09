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
        
        this.path = metadata.path; 
        
        this.container = new St.BoxLayout({vertical: true, style_class: 'jarvis-box'});
        
        this.addButton("Clock", "set-screen/clock","clock");
        this.addButton("Weather", "set-screen/weather","weather");
        this.addButton("Performance", "set-screen/performance","performance");
        this.addButton("Sensor", "set-screen/sensors","sensors");
        this.addButton("Network", "set-screen/net-traffic","net-traffic");
        this.addButton("Calendar", "set-screen/calendar","calendar");
        this.addSimpleButton("AUTO MODE", "set-mode/auto");

        this.setContent(this.container);
    },

    addSimpleButton: function(label, path) {
        let btn = new St.Button({label: label, style_class: 'jarvis-button'});
        btn.connect('button-release-event', () => {
            Util.spawnCommandLine('curl -X POST http://localhost:8000/' + path);
        });
        this.container.add(btn);
    },

    addButton: function(label, path, id) {
        let box = new St.BoxLayout({vertical: false});
        
        // Log para depurar: vamos a ver qué está llegando
        global.log("Agregando botón: " + label + " con ID: " + id);
        
        if (id !== undefined && id !== null) {
            global.log("¡Creando checkbox para " + id + "!");
            let checkBtn = new St.Button({label: "[X]", style_class: 'jarvis-button'});
            let isChecked = true;

            checkBtn.connect('button-release-event', () => {
                isChecked = !isChecked;
                checkBtn.label = isChecked ? "[X]" : "[ ]";
                Util.spawnCommandLine(`curl -X POST http://localhost:8000/set-active/${id}/${isChecked ? 'enable' : 'disable'}`);
            });
            box.add(checkBtn);
        } else {
            global.log("No hay ID, saltando checkbox para: " + label);
        }
        
        let btn = new St.Button({label: label, style_class: 'jarvis-button'});
        btn.connect('button-release-event', () => {
            Util.spawnCommandLine('curl -X POST http://localhost:8000/' + path);
        });

        box.add(btn);
        this.container.add(box);
    },
};

function main(metadata) {
    return new JarvisDesklet(metadata);
}
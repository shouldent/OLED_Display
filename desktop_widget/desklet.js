const Desklet = imports.ui.desklet;
const St = imports.gi.St;
const Util = imports.misc.util;
const Gio = imports.gi.Gio; // Necesario para leer archivos
const ByteArray = imports.byteArray; // Necesario para convertir el contenido

function JarvisDesklet(metadata) {
    this._init(metadata);
}

JarvisDesklet.prototype = {
    __proto__: Desklet.Desklet.prototype,

    _init: function(metadata) {
        Desklet.Desklet.prototype._init.call(this, metadata);
        
        this.path = metadata.path; 
        
        // --- LEER JSON DE ESTADOS ---
        let status = {};
        let file = Gio.File.new_for_path(this.path + '/status.json');
        
        try {
            let [success, contents] = file.load_contents(null);
            if (success) {
                status = JSON.parse(ByteArray.toString(contents));
                global.log("JSON de estado cargado correctamente.");
            }
        } catch (e) {
            global.log("No se pudo leer status.json, usando valores por defecto.");
            status = {"clock": true, "weather": true, "performance": false, "sensors": false, "network": false, "net-traffic": false, "calendar": true};
        }
        // -----------------------------

        this.container = new St.BoxLayout({vertical: true, style_class: 'jarvis-box'});
        
        // Pasamos el estado leído del JSON al cuarto parámetro
        this.addButton("Clock", "set-screen/clock", "clock", status["clock"]);
        this.addButton("Weather", "set-screen/weather", "weather", status["weather"]);
        this.addButton("Performance", "set-screen/performance", "performance", status["performance"]);
        this.addButton("Sensor", "set-screen/sensors", "sensors", status["sensors"]);
        this.addButton("Network", "set-screen/net-traffic", "network", status["network"]); // Asegúrate que el ID coincida con tu JSON
        this.addButton("Calendar", "set-screen/calendar", "calendar", status["calendar"]);
        
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

    addButton: function(label, path, id, isEnable = false) {
        let box = new St.BoxLayout({vertical: false});
        
        if (id !== undefined && id !== null) {
            let isChecked = isEnable;
            let checkBtn = new St.Button({
                label: isChecked ? "[X]" : "[ ]", 
                style_class: 'jarvis-button'
            });
            
            checkBtn.connect('button-release-event', () => {
                isChecked = !isChecked;
                checkBtn.label = isChecked ? "[X]" : "[ ]";
                Util.spawnCommandLine(`curl -X POST http://localhost:8000/set-active/${id}/${isChecked ? 'enable' : 'disable'}`);
            });
            box.add(checkBtn);
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
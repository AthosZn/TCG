function toggleShow(id) {
    if (document.getElementById(id).style.display === 'block')
        document.getElementById(id).style.display = 'none';
    else
        document.getElementById(id).style.display = 'block';
}

function flipCard (card, div, card_type, name, desc_text, cost, creature_strength, counter) {
    document.getElementById('sub_card').style.display = 'block';
    if (counter === null)
        document.getElementById("card_img").innerHTML = "<img src=\"Card_"+card_type+".png\"></img>"
    else
        document.getElementById("card_img").innerHTML = "<img src=\"Card_"+card_type+"_counter.png\"></img>"
            document.getElementById("card_name").innerHTML = name;
    document.getElementById("card_desc").innerHTML = desc_text;
    var i;
    var costbar="";
    for (i=0;i<cost;i++){
        costbar +="<img src=\"Mana.png\"></img>"
    }
    document.getElementById("card_cost").innerHTML =costbar ;
    if (creature_strength){
        document.getElementById("card_strength").innerHTML = creature_strength;
        if (counter !== null) {
            document.getElementById("card_counter").innerHTML = counter;
        }
        else {
            document.getElementById("card_counter").innerHTML = "";
        }
    }
    else if (counter !== null){
        document.getElementById("card_strength").innerHTML = counter;
        document.getElementById("card_counter").innerHTML = "";
    }
    else {
        document.getElementById("card_counter").innerHTML = "";
        document.getElementById("card_strength").innerHTML = "";
    }
}

function ajaxSend (url, args) {
    var xmlhttp = new XMLHttpRequest(); 
    xmlhttp.open("POST",url,true);
    xmlhttp.setRequestHeader("Content-type","application/x-www-form-urlencoded");
    xmlhttp.send(args);
}
function sendHand (gid, hnum) {
    ajaxSend ("/play","handnum="+hnum+"&gameid="+gid)
}
function draw (gid) {
    ajaxSend ("/draw","gameid="+gid)
}
function growMana (gid) {
    ajaxSend ("/grow_mana","gameid="+gid)
}
function use_item (gid, iid){
    ajaxSend("/activate_item", "gameid="+gid+"&iid="+iid)
}
function activate (gid, cid){
    ajaxSend("/activate_creature", "gameid="+gid+"&cid="+cid)
}
function sendAttack (gid, length){
    sendCheckBoxes("/attack", gid, length)
}
function sendBlock (gid, length){
    sendCheckBoxes("/block", gid, length)
}
function sendKill (gid, length){
    sendCheckBoxes("/kill", gid, length)
}
function sendSelect (gid, length){
    sendCheckBoxes("/select", gid, length)
}
function sendCheckBoxes (url, gid, length){
    var boolArray = new Array (length);
    for (id = 0; id < length; id++){
        var attacker = document.getElementById ("c"+id);
        boolArray[id] = attacker.checked;
    }
    ajaxSend (url,"gameid="+gid+"&checkboxes="+JSON.stringify(boolArray))
}

function dispManaBar (cur, max){
    var manabar = "";
    for (i = 0; i < cur; i++)
        manabar += "<img src=\"Mana.png\"></img>";
    for (i = cur; i < max; i++)
        manabar += "<img src=\"Mana_empty.png\"></img>";
    return manabar;
}


if ("WebSocket" in window){
    //var source = new WebSocket("ws://localhost:8888/socket");
    var source = new WebSocket("ws://192.168.0.24:8888/socket");
    //var source = new WebSocket("ws://195.154.45.210:8888/socket");
    source.onmessage = function(event) {
        var parse_json = JSON.parse (event.data);
        if ("self_state" in parse_json){
            disp_pcards (parse_json.self_state, 
                ["hand","creatures","items","graveyard"], 
                parse_json.on_trait, parse_json.attackers, parse_json.blockers, 
                parse_json.get_killed, parse_json.gid, parse_json.get_target);
            var pstatus = document.getElementById("pstatus");
            var manabar = dispManaBar (parse_json.self_state.cur_mana, parse_json.self_state.max_mana)
            pstatus.innerHTML = "<img src=heart-icon.png></img>x" + parse_json.self_state.health + " Mana:" + manabar
            if (parse_json.on_trait && !(parse_json.attackers.length>0)) {
                pstatus.innerHTML += " <button type=\"button\" onclick=growMana("+
                    parse_json.gid+")>Grow mana</button>";
            }
        }
        if ("opp_state" in parse_json){
            disp_pcards (parse_json.opp_state, 
                ["opp_creatures","opp_items","opp_graveyard"], 
                parse_json.on_trait, parse_json.attackers, parse_json.blockers, 
                parse_json.get_killed, parse_json.gid, parse_json.get_target);
            var oppstatus = document.getElementById("oppstatus");
            var manabar = dispManaBar (parse_json.opp_state.opp_cur_mana, 
                    parse_json.opp_state.opp_max_mana)
            opp_status.innerHTML = "<img src=heart-icon.png></img>x"
                     + parse_json.opp_state.opp_health + " Mana:" +  manabar +
                                "<br>Hand: " + parse_json.opp_state.opp_hand + " card(s)";
        }
        if ("log" in parse_json){
            var logdiv = document.getElementById("logger");
            logdiv.innerHTML += parse_json.log; 
            logdiv.scrollTop = 100000
        }
        if ("game_over" in parse_json){
            window.location.replace (parse_json.game_over);
        }
    //    if ("require_target" in parse_json) {
    //        var htmltab = document.getElementById (parse_json.require_target);
    //        var table = htmltab.firstChild.firstChild;
    //        if (table != null) {
    //            var header = table.firstChild;
    //            var targetElement = document.createElement ("th")
    //            var targetText = document.createTextNode ("Target")
    //            targetElement.appendChild (targetText)
    //            header.appendChild (targetElement)
    //            for (i=1; i<table.childNodes.length; i++){
    //            }
    //        }
    //    }
    };
}
else {
    alert ("WebSocket not supported! You can't play the game until a workararound is implemented. Mail the project owner!")
}

function disp_pcards (parse_json, targetlist, on_trait, attackers, blockers, get_killed, gid, get_target) {
    for (cardindex in targetlist){
        var varhand = document.getElementById(targetlist[cardindex]);
        var listname = targetlist[cardindex];
        if (parse_json[listname].length === 0){
            varhand.innerHTML = ""
            continue;
        }
        var mytab = "<table>";
        var main_turn = on_trait && attackers.length==0;
        var can_select = listname === get_target && on_trait
        var can_attack = listname === "creatures" && main_turn && !can_select
        var can_block = listname === "creatures" && !on_trait && attackers.length>0 && !get_killed;
        var get_opp_kills = listname === "opp_creatures" && !on_trait && get_killed === "attacking";
        var get_self_kills = listname === "creatures" && !on_trait && get_killed === "blocking";
        var show_attackers = listname === "opp_creatures" && !on_trait && attackers.length>0 && !get_killed;
        var can_activate_item = listname === "items" && main_turn && !can_select
        var can_activate_creature = listname === "creatures" && main_turn && !can_select
        var can_play = listname === "hand" && main_turn && !can_select

        if (can_play){
            mytab += "<button type=\"button\" onclick=draw("+gid+")>Draw</button>"
        }

        mytab += "<tr>";
        if (listname === "hand"){
            mytab += "<th>Cards</th>";
        }
        else if (listname === "creatures" || listname === "opp_creatures"){
            mytab += "<th>Creatures</th>";
        }
        else if (listname === "items" || listname === "opp_items"){
            mytab += "<th>Items</th>";
        }
        else if (listname === "graveyard" || listname === "opp_graveyard"){
            mytab += "<th>Cards</th>";
        }
        if (listname === "hand"){
            mytab += "<th>Cost</th>";
        }
        if (listname === "creatures" || listname === "opp_creatures"){
            mytab += "<th>Strength</th>";
        }
        if (can_play) {
            mytab += "<th>Action</th>";
        }
        if (can_activate_item || can_activate_creature) {
            mytab += "<th>Activate</th>";
        }
        if (get_opp_kills || get_self_kills){
            mytab += "<th>Kill creatures</th>";
        }
        else if (can_select) {
            mytab += "<th>Select</th>";
        }
        else if (can_attack) { 
            mytab += "<th>Attack</th>";
        }
        else if (show_attackers){
            mytab += "<th>Attackers</th>";
        }
        else if (can_block) {
            mytab += "<th>Block</th>";
        }
        mytab += "</tr>";
        for (item in parse_json[listname]){
            var colorcode = "#ffffff"
            var ctype = parse_json[listname][item].card_type
            if (ctype === "creature")
                colorcode = "#a0ffa0";
            else if (ctype === "item")
                colorcode = "#ffee88";
            else if (ctype === "sorcery")
                colorcode = "#a0a0ff";
            var div = "self_div";
            var card = "self_card";
            if (listname === "opp_items" || listname === "opp_creatures" || listname === "opp_graveyard"){
                div = "opp_div";
                card = "opp_card";
            }
            mytab += "<tr title=\""+ ctype + ": " + parse_json[listname][item].desc_text +
                "\"/tr><td onclick=\"flipCard(\'"+card +"\',\'"+div+"\',\'"+ctype+"\',\'"+
                parse_json[listname][item].name+"\',\'"+parse_json[listname][item].desc_text+
                "\',\'"+parse_json[listname][item].cost+"\',"+
                parse_json[listname][item].creature_strength+","+parse_json[listname][item].counter+")\" style=\"background:"+
                colorcode+"\">" + parse_json[listname][item].name + "</td>";
            if (listname === "hand"){
                mytab += "<td>" + parse_json[listname][item].cost + "</td>";
            }
            if (listname === "creatures" || listname === "opp_creatures"){
                mytab += "<td>" + (parse_json[listname][item].creature_strength || "--") + "</td>";
            }
            if (can_play){
                if (parse_json[listname][item].cost <= parse_json.cur_mana){
                    mytab += "<td><button type=\"button\" onclick=sendHand("+gid+","+item+")>Play</button></td>";
                }
                else {
                    mytab += "<td></td>"
                }
            }
            
            else if (can_activate_creature ){
                if (parse_json[listname][item].is_activable)
                mytab += "<td><button type=\"button\" onclick=activate("+gid+","+item+")>Use effect</button></td>";
                else
                    mytab += "<td></td>"
            }
            else if (can_activate_item ){
                if (parse_json[listname][item].is_activable){
                    mytab += "<td><button type=\"button\" onclick=use_item("+gid+","+item+")>Use effect</button></td>";
                }
                else {
                    mytab += "<td></td>"
                }
            }
            if (can_select){ 
                mytab += "<td><input type=\"radio\" id=\"c"+item+"\" name=\"get_target\"></input></td>";
            }
            else if (listname === "creatures" && (can_attack || can_block || get_self_kills)){ 
                mytab += "<td><input type=\"checkbox\" id=\"c"+item+"\"></input></td>";
            }
            else if (show_attackers){
                if (attackers[item]){
                    mytab += "<td>Attacking</td>";
                }
                else {
                    mytab += "<td></td>";
                }
            }
            else if (listname === "opp_creatures" && get_opp_kills){
                mytab += "<td><input type=\"checkbox\" id=\"c"+item+"\"></input></td>";
            }
            mytab += "</tr>";
        }
        mytab += "</table>";
        if (get_self_kills){
            mytab += "<button type=\"button\" onclick=sendKill("+gid+","+
                    parse_json[listname].length+")>Sacrifice</button>";
        }
        else if (can_select) {
            mytab += "<button type=\"button\" onclick=sendSelect("+gid+","+
                    parse_json[listname].length+")>Select target</button>";
        }
        else if (get_opp_kills){
            mytab += "<button type=\"button\" onclick=sendKill("+gid+","+
                    parse_json[listname].length+")>Kill</button>";
        }
        else if (can_attack) { 
            mytab += "<button type=\"button\" onclick=sendAttack("+gid+","+
                    parse_json[listname].length+")>Attack</button>";
        }
        else if (can_block) {
            mytab += "<button type=\"button\" onclick=sendBlock("+gid+","+
                    parse_json[listname].length+")>Block</button>";
        }
        varhand.innerHTML = mytab;
    }
};

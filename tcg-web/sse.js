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
function sendCheckBoxes (url, gid, length){
    var boolArray = new Array (length);
    for (id = 0; id < length; id++){
        var attacker = document.getElementById ("c"+id);
        boolArray[id] = attacker.checked;
    }
    ajaxSend (url,"gameid="+gid+"&creatures="+JSON.stringify(boolArray))
}

var source = new WebSocket("ws://localhost:8888/socket");
source.onmessage = function(event) {
    var parse_json = JSON.parse (event.data);
    if ("pstate" in parse_json){
        disp_pcards (parse_json.pstate, 
            ["hand","creatures","items","graveyard"], 
            ["hand","creatures","items","graveyard"], 
            parse_json.on_trait, parse_json.attackers, parse_json.blockers, parse_json.get_killed, parse_json.gid);
        var pstatus = document.getElementById("pstatus");
        pstatus.innerHTML = "<b>HP: " + parse_json.pstate.health +
                            " MP: " + parse_json.pstate.cur_mana + "/" +
                            parse_json.pstate.max_mana + "</b>" ;
        if (parse_json.on_trait && !(parse_json.attackers.length>0)) {
            pstatus.innerHTML += " <button type=\"button\" onclick=draw("+parse_json.gid+")>Draw</button><button type=\"button\" onclick=growMana("+
                parse_json.gid+")>Grow mana</button>";
        }
    }
    if ("oppstate" in parse_json){
        disp_pcards (parse_json.oppstate, 
            ["creatures", "items","graveyard"], 
            ["opp_creatures","opp_items","opp_graveyard"], 
             parse_json.on_trait, parse_json.attackers, parse_json.blockers, parse_json.get_killed, parse_json.gid);
        var oppstatus = document.getElementById("oppstatus");
        opp_status.innerHTML = "<b>Opponent HP: " + parse_json.oppstate.health +
                            " MP: " + parse_json.oppstate.cur_mana + "/" +
                            parse_json.oppstate.max_mana +
                            " hand: " + parse_json.oppstate.hand + " card(s)</b>";
    }
};

function disp_pcards (parse_json, serverlist, targetlist, on_trait, attackers, blockers, get_killed, gid) {
    for (cardindex in serverlist){
        var varhand = document.getElementById(targetlist[cardindex]);
        var listname = serverlist[cardindex];
        if (parse_json[listname].length === 0){
            varhand.innerHTML = "Empty"
            continue;
        }
        var mytab = "<table>";
        var can_attack = targetlist[cardindex] === "creatures" && on_trait && attackers.length==0;
        var can_block = targetlist[cardindex] === "creatures" && !on_trait && attackers.length>0 && !get_killed;
        var can_play = targetlist[cardindex] === "hand" && on_trait && attackers.length==0
        var get_opp_kills = targetlist[cardindex] === "opp_creatures" && !on_trait && get_killed === "attacking";
        var get_self_kills = targetlist[cardindex] === "creatures" && !on_trait && get_killed === "blocking";
        var show_attackers = targetlist[cardindex] === "opp_creatures" && !on_trait && attackers.length>0 && !get_killed;
        var can_activate_item = targetlist[cardindex] === "items" && on_trait && attackers.length==0;
        var can_activate_creature = targetlist[cardindex] === "creatures" && on_trait && attackers.length==0;
             
        mytab += "<tr><th>Card</th>";
        if (targetlist[cardindex] === "hand"){
            mytab += "<th>Card type</th>";
            mytab += "<th>Cost</th>";
        }
        if (targetlist[cardindex] === "hand" || listname === "creatures"){
            mytab += "<th>Strength</th>";
        }
        if (can_play) {
            mytab += "<th>Action</th>";
        }
        if (get_opp_kills || get_self_kills){
            mytab += "<th>Kill creatures</th>";
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
        if (can_activate_item || can_activate_creature) {
            mytab += "<th>Activate</th>";
        }
        mytab += "</tr>";
        for (item in parse_json[listname]){
            mytab += "<td title=\""+ parse_json[listname][item].desc_text +"\">" + parse_json[listname][item].name + "</td>";
            if (targetlist[cardindex] === "hand"){
                mytab += "<td>" + parse_json[listname][item].card_type + "</td>";
                mytab += "<td>" + parse_json[listname][item].cost + "</td>";
            }
            if (targetlist[cardindex] === "hand" || listname === "creatures"){
                mytab += "<td>" + (parse_json[listname][item].creature_strength || "--") + "</td>";
            }
            if (can_play) {
                mytab += "<td><button type=\"button\" onclick=sendHand("+gid+","+item+")>Play</button></td>";
            }
            else if (can_activate_creature && parse_json[listname][item].is_activable){
                mytab += "<td><button type=\"button\" onclick=activate("+gid+","+item+")>Use effect</button></td>";
            }
            else if (can_activate_item && parse_json[listname][item].is_activable){
                mytab += "<td><button type=\"button\" onclick=use_item("+gid+","+item+")>Use effect</button></td>";
            }
            else if (targetlist[cardindex] === "creatures" && (can_attack || can_block || get_self_kills)){ 
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
            else if (targetlist[cardindex] === "opp_creatures" && get_opp_kills){
                mytab += "<td><input type=\"checkbox\" id=\"c"+item+"\"></input></td>";
            }
            mytab += "</tr>";
        }
        mytab += "</table>";
        if (get_self_kills){
            mytab += "<button type=\"button\" onclick=sendKill("+gid+","+
                    parse_json[listname].length+")>Sacrifice</button>";
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

// --- CONFIG ---
const viewState = window.VISO_VIEW || {};
const jefeUser = viewState.jefeUser || '';
const reportBasePath = viewState.reportBasePath || '';
const headers = viewState.headers || [];
const canDelete = Boolean(viewState.canDelete);
const canEdit = Boolean(viewState.canEdit);
const currentModule = viewState.currentModule || '';

// --- STATE ---
let filteredData = [];
let currentOffset = 0;
const LIMIT = 50;
let isLoading = false;

const isInventory = (currentModule === 'inventario' || currentModule === 'productos');

// --- MAIN FETCH ---
function fetchData(reset = false) {
    if (isLoading) return;
    
    if (reset) {
        currentOffset = 0;
        const tbody = document.getElementById('tableBody');
        const grid = document.getElementById('gridContainer');
        if(tbody) tbody.innerHTML = '';
        if(grid) grid.innerHTML = '';
        filteredData = [];
    }
    
    isLoading = true;
    
    const searchInp = document.getElementById('searchInput');
    const q = searchInp ? searchInp.value : '';
    const cat = document.getElementById('filterCategory') ? document.getElementById('filterCategory').value : '';
    const brand = document.getElementById('filterBrand') ? document.getElementById('filterBrand').value : '';
    
    const btn = document.getElementById('loadMoreBtn');
    if(btn) btn.innerText = 'Cargando...';

    let url = "/api/list?module=" + currentModule + "&q=" + encodeURIComponent(q) + "&offset=" + currentOffset + "&limit=" + LIMIT;
    if(cat) url += "&category=" + encodeURIComponent(cat);
    if(brand) url += "&brand=" + encodeURIComponent(brand);
    
    fetch(url)
    .then(function(r) { return r.json(); })
    .then(function(res) {
        filteredData = filteredData.concat(res.data);
        
        if (isInventory) {
            renderCards(res.data);
        } else {
            renderRows(res.data);
        }
        
        currentOffset += res.data.length;
        
        const counter = document.getElementById('counterLabel');
        if(counter) counter.innerText = "Mostrando " + currentOffset + " de " + res.total;
        
        const loadMore = document.getElementById('loadMoreContainer');
        if(loadMore) {
            loadMore.style.display = (currentOffset < res.total) ? 'block' : 'none';
            if(btn) btn.innerText = 'Cargar mas...';
        }
        
        const empty = document.getElementById('emptyState');
        if(empty) {
            empty.style.display = (currentOffset === 0 && res.total === 0) ? 'block' : 'none';
        }
        
        isLoading = false;
    })
    .catch(function(e) {
        console.error("Error fetchData:", e);
        isLoading = false;
        if(btn) btn.innerText = 'Error';
    });
}

function renderRows(batch) {
    const tbody = document.getElementById('tableBody');
    if(!tbody) return;
    
    batch.forEach(function(row, index) {
        const globalIndex = (filteredData.length - batch.length) + index;
        let html = "";
        
        headers.forEach(function(key) {
            html += "<td>" + formatValue(row[key], key) + "</td>";
        });
        
        let actions = "";
        const idKey = ['id', 'codigo', 'dni'].find(function(k) { return row[k]; }) || 'id';
        
        if (currentModule === 'ventas') {
            actions += "<button onclick=\"event.stopPropagation(); downloadPDF('" + (row.numero_boleta || row.id) + "')">PDF</button>";
        }
        
        if(canEdit) actions += "<button onclick=\"event.stopPropagation(); openEditModal(" + globalIndex + ")">Edit</button>";
        if(canDelete) actions += "<button onclick=\"event.stopPropagation(); deleteItem('" + row[idKey] + "')">Del</button>";
        
        tbody.insertAdjacentHTML('beforeend', "<tr onclick=\"showDetails(" + globalIndex + ")">" + html + "<td>" + actions + "</td></tr>");
    });
}

function renderCards(batch) {
    const container = document.getElementById('gridContainer');
    if(!container) return;
    
    batch.forEach(function(row, index) {
        const globalIndex = (filteredData.length - batch.length) + index;
        const stock = parseInt(row.stock || 0);
        
        let imgSrc = "";
        if(row.image_path) {
            imgSrc = "/serve_image?path=" + encodeURIComponent(row.image_path);
        }
        
        const imgHtml = imgSrc ? "<img src=\"" + imgSrc + "\">" : "<div>BOX</div>";
            
        const cardHtml = "<div class=\"product-card\" onclick=\"showDetails(" + globalIndex + ")">" +
            "<div class=\"product-image\">" + imgHtml + "</div>" +
            "<div class=\"product-info\">" +
                "<div>" + (row.categoria || 'Gral') + "</div>" +
                "<strong>" + (row.nombre || 'Prod') + "</strong>" +
                "<div>S/ " + parseFloat(row.venta || 0).toFixed(2) + " (Stk: " + stock + ")</div>" +
            "</div>" +
            "<div class=\"card-actions\">" +
                "<button onclick=\"event.stopPropagation(); openStockModal(" + globalIndex + ")">Stock</button>" +
                "<button onclick=\"event.stopPropagation(); openEditModal(" + globalIndex + ")">Edit</button>" +
            "</div>" +
        "</div>";
        
        container.insertAdjacentHTML('beforeend', cardHtml);
    });
}

function formatValue(val, key) {
    if (val === null || val === undefined) return '-';
    if (['venta', 'total', 'precio'].includes(key)) return "S/ " + parseFloat(val).toFixed(2);
    return val;
}

function downloadPDF(id) {
    const url = "/serve_image?path=" + encodeURIComponent(reportBasePath.replace(/\\/g, '/') + "/boleta_" + id + ".pdf");
    window.open(url, '_blank');
}

// --- GLOBALS ---
window.openModal = function() {
    document.getElementById('createModal').style.display = 'flex';
};

window.openPOSModal = function() {
    document.getElementById('posModal').style.display = 'flex';
    fetch('/api/list?module=inventario&limit=5000')
    .then(function(r) { return r.json(); })
    .then(function(res) {
        const list = document.getElementById('posProductList');
        list.innerHTML = res.data.map(function(p) {
            return "<div onclick=\"addToCart('" + p.codigo + "')">" + p.nombre + " - S/ " + p.venta + "</div>";
        }).join('');
    });
};

window.closePOSModal = function() { document.getElementById('posModal').style.display = 'none'; };
window.closeModal = function() { document.getElementById('createModal').style.display = 'none'; };
window.closeDetailsModal = function() { document.getElementById('detailsModal').style.display = 'none'; };

window.showDetails = function(idx) {
    const row = filteredData[idx];
    alert(JSON.stringify(row, null, 2));
};

function initTable() {
    const invFilters = document.getElementById('inventoryFilters');
    if(invFilters) invFilters.style.display = isInventory ? 'block' : 'none';

    if (isInventory) {
        document.getElementById('gridContainer').style.display = 'grid';
        document.getElementById('tableContainer').style.display = 'none';
    } else {
        const thead = document.getElementById('tableHeaders');
        if(thead) {
            let h = headers.map(function(x) { return "<th>" + x.toUpperCase() + "</th>"; }).join('');
            thead.innerHTML = h + "<th>Acciones</th>";
        }
    }
    fetchData(true);
}

document.getElementById('loadMoreBtn').onclick = function() { fetchData(false); };
document.getElementById('searchInput').oninput = function() { fetchData(true); };

initTable();

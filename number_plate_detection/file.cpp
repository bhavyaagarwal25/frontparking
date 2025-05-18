#include <iostream>
#include <vector>
#include <queue>
#include <set>
#include <limits>
#include <iomanip>
#include <algorithm>
using namespace std;

// ANSI color codes
const string RST = "\033[0m";
const string RED = "\033[1;31m";   // occupied
const string GRN = "\033[1;32m";   // empty
const string BLU = "\033[1;34m";   // entry→slot path
const string MAG = "\033[1;35m";   // slot→exit path

constexpr int ROWS = 5, COLS = 10;
constexpr int TOTAL_SLOTS = ROWS * COLS;
constexpr int ENTRY_NODE = 0;
constexpr int EXIT_NODE  = TOTAL_SLOTS + 1;  // 51

// adjacency list: nodes 0..51
vector<vector<pair<int,int>>> adj;

// Dijkstra without structured bindings
// returns pair: first = dist[], second = parent[]
pair<vector<int>, vector<int>> dijkstra(int src) {
    int N = TOTAL_SLOTS + 2;
    const int INF = numeric_limits<int>::max();
    vector<int> dist(N, INF), par(N, -1);
    dist[src] = 0;

    // min‑heap (dist, node)
    priority_queue< pair<int,int>,
                    vector<pair<int,int>>,
                    greater<pair<int,int>> > pq;
    pq.push(make_pair(0, src));

    while (!pq.empty()) {
        pair<int,int> top = pq.top(); 
        pq.pop();
        int d = top.first;
        int u = top.second;
        if (d > dist[u]) continue;

        for (size_t i = 0; i < adj[u].size(); ++i) {
            int v = adj[u][i].first;
            int w = adj[u][i].second;
            if (d + w < dist[v]) {
                dist[v] = d + w;
                par[v]  = u;
                pq.push(make_pair(dist[v], v));
            }
        }
    }
    return make_pair(dist, par);
}

// Reconstruct chain from src to target by following parents
vector<int> buildChain(int target, const vector<int>& par) {
    vector<int> chain;
    for (int u = target; u != -1; u = par[u]) {
        chain.push_back(u);
    }
    reverse(chain.begin(), chain.end());
    return chain;
}

// Generate human directions from a chain of node IDs
vector<string> getDirections(const vector<int>& c) {
    vector<string> dirs;
    for (size_t i = 0; i + 1 < c.size(); ++i) {
        int u = c[i], v = c[i+1];
        if (u == ENTRY_NODE && v != EXIT_NODE) {
            dirs.push_back("Enter at slot " + to_string(v));
        }
        else if (v == EXIT_NODE && u != ENTRY_NODE) {
            dirs.push_back("Exit from slot " + to_string(u));
        }
        else {
            int ur = (u-1)/COLS, uc = (u-1)%COLS;
            int vr = (v-1)/COLS, vc = (v-1)%COLS;
            if      (vr == ur+1) dirs.push_back("Down to slot "  + to_string(v));
            else if (vr == ur-1) dirs.push_back("Up to slot "    + to_string(v));
            else if (vc == uc+1) dirs.push_back("Right to slot " + to_string(v));
            else if (vc == uc-1) dirs.push_back("Left to slot "  + to_string(v));
        }
    }
    return dirs;
}

// Print ASCII map, legend, and path lengths
void printMap(int target,
              const set<int>& occupied,
              const vector<bool>& pET,
              const vector<bool>& pTE,
              int dET, int dTE)
{
    int occ = occupied.size();
    int emp = TOTAL_SLOTS - occ;

    cout << "           " << BLU << "ENTRY" << RST << "\n\n";
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int s = r*COLS + c + 1;
            string col;
            if      (pET[s])            col = BLU;
            else if (pTE[s])            col = MAG;
            else if (occupied.count(s)) col = RED;
            else                        col = GRN;
            cout << col << setw(2) << setfill('0') << s << RST << "  ";
        }
        if (r == 1) cout << "   Total:   " << TOTAL_SLOTS;
        if (r == 2) cout << "   Empty:   " << emp;
        if (r == 3) cout << "   Occpd:   " << occ;
        cout << "\n";
    }
    cout << "\n           " << MAG << "EXIT" << RST << "\n\n";
    cout << BLU
         << "ENTRY->" << setw(2) << setfill('0') << target
         << " = " << dET << " steps" << RST << "\n";
    cout << MAG
         << setw(2) << setfill('0') << target << "->EXIT"
         << " = " << dTE << " steps" << RST << "\n\n";
    cout << "Legend: "
         << GRN << "Green"   << RST << "=empty  "
         << RED << "Red"     << RST << "=occupied  "
         << BLU << "Blue"    << RST << "=entry path  "
         << MAG << "Magenta" << RST << "=exit path\n\n";
}

int main(){
    // 1) Build graph
    adj.assign(TOTAL_SLOTS+2, vector<pair<int,int>>());
    auto add = [&](int u,int v,int w){
        adj[u].push_back(make_pair(v,w));
        adj[v].push_back(make_pair(u,w));
    };

    // Connect every slot ↔ ENTRY & EXIT with high cost
    const int HIGH = 1000;
    for (int s = 1; s <= TOTAL_SLOTS; ++s) {
        add(ENTRY_NODE, s, HIGH);
        add(s, EXIT_NODE, HIGH);
    }
    // Connect grid neighbors with cost=1
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int u = r*COLS + c + 1;
            if (c+1 < COLS) add(u, u+1, 1);
            if (r+1 < ROWS) add(u, u+COLS, 1);
        }
    }

    // 2) Occupied slots
    set<int> occupied = {5, 18, 26, 33, 42};

    // 3) Target slot
    int target = 33;

    // 4) Dijkstra ENTRY -> all
    pair<vector<int>,vector<int>> et = dijkstra(ENTRY_NODE);
    vector<int> distET = et.first, parET = et.second;

    // 5) Dijkstra EXIT -> all
    pair<vector<int>,vector<int>> te = dijkstra(EXIT_NODE);
    vector<int> distTE = te.first, parTE = te.second;

    // 6) Build chains
    vector<int> chainET = buildChain(target, parET);
    vector<int> chainTE = buildChain(EXIT_NODE, parTE);

    // 7) Mark flags
    vector<bool> pET(TOTAL_SLOTS+2, false), pTE(TOTAL_SLOTS+2,false);
    for (int u : chainET) pET[u] = true;
    for (int u : chainTE) pTE[u] = true;

    // 8) Print map & legend
    printMap(target, occupied,
             pET, pTE,
             distET[target], distTE[target]);

    // 9) Print directions
    vector<string> dirsET = getDirections(chainET);
    cout << "Directions ENTRY->" << target << ":\n";
    for (size_t i = 0; i < dirsET.size(); ++i)
        cout << "  - " << dirsET[i] << "\n";

    vector<string> dirsTE = getDirections(chainTE);
    cout << "\nDirections " << target << "->EXIT:\n";
    for (size_t i = 0; i < dirsTE.size(); ++i)
        cout << "  - " << dirsTE[i] << "\n";

    return 0;
}
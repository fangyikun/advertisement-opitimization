export interface Condition {
  type: 'weather' | 'time' | 'holiday';
  operator: '==' | 'in' | 'between';
  value: string;
}

export interface Action {
  type: 'switch_playlist';
  target_id: string;
}

export interface Rule {
  name: string;
  priority: number;
  conditions: Condition[];
  action: Action;
}
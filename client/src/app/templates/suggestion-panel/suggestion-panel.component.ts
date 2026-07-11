import {Component, EventEmitter, Input, Output} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {NgIf} from '@angular/common';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

@Component({
  selector: 'app-suggestion-panel', standalone: true,
  imports: [FormsModule, NgIf, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatFormFieldModule, MatInputModule],
  templateUrl: './suggestion-panel.component.html', styleUrl: './suggestion-panel.component.css'
})
export class SuggestionPanelComponent {
  @Input() disabled = false
  @Input() isLoading = false
  @Input() error: string | null = null
  @Output() suggest = new EventEmitter<string>()
  context = ''
}

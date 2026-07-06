import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {TranslateModule} from "@ngx-translate/core";
import {MatIconModule} from "@angular/material/icon";

@Component({
  standalone: true,
  selector: 'confirmation1',
  templateUrl: './confirmation-dialog.component.html',
  imports: [
    MatButtonModule,
    TranslateModule,
    MatDialogModule,
    MatIconModule
  ],
  styleUrls: ['./confirmation-dialog.component.css']
})
export class ConfirmationDialogComponent implements OnInit {

  confirmationMessage = 'Cette action est irreversible. Voulez-vous vraiment continuer ?';
  extraActionLabel: string | null = null;

  constructor(
    public dialogRef: MatDialogRef<ConfirmationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) {
    if (Object.keys(data).indexOf('confirmationMessage') > -1 && data.confirmationMessage) {
      this.confirmationMessage = data.confirmationMessage;
    }
    if (Object.keys(data).indexOf('extraActionLabel') > -1 && data.extraActionLabel) {
      this.extraActionLabel = data.extraActionLabel;
    }
  }

  ngOnInit() {
  }

  cancel(): void {
    this.dialogRef.close(false);
  }

  confirm(): void {
    this.dialogRef.close(true);
  }

  confirmExtra(): void {
    this.dialogRef.close('extra');
  }
}

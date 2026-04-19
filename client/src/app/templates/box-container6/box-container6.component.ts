// box-container6.component.ts
import { Component, AfterViewInit, ElementRef } from '@angular/core';

@Component({
  selector: 'app-box-container6',
  standalone: true,
  templateUrl: './box-container6.component.html',
  styleUrls: ['./box-container6.component.css']
})
export class BoxContainer6Component implements AfterViewInit {
  constructor(private elementRef: ElementRef) {}

  ngAfterViewInit(): void {

  }
}
